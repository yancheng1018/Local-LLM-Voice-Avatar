import os
import json
from typing import Callable
from loguru import logger
from fastapi import WebSocket

from prompts import prompt_loader
from .live2d_model import Live2dModel
from .asr.asr_interface import ASRInterface
from .tts.tts_interface import TTSInterface
from .vad.vad_interface import VADInterface
from .agent.agents.agent_interface import AgentInterface
from .translate.translate_interface import TranslateInterface

from .mcpp.server_registry import ServerRegistry
from .mcpp.tool_manager import ToolManager
from .mcpp.mcp_client import MCPClient
from .mcpp.tool_executor import ToolExecutor
from .mcpp.tool_adapter import ToolAdapter

from .asr.asr_factory import ASRFactory
from .tts.tts_factory import TTSFactory
from .vad.vad_factory import VADFactory
from .agent.agent_factory import AgentFactory
from .translate.translate_factory import TranslateFactory

from .config_manager import (
    Config,
    AgentConfig,
    CharacterConfig,
    SystemConfig,
    ASRConfig,
    TTSConfig,
    VADConfig,
    TranslatorConfig,
    read_yaml,
    validate_config,
    apply_default_character,
)

# 角色语言代码 -> (英文名, 该语言自称)，用于生成 system prompt 里的语言指令。
# 键与 CharacterConfig.language 的白名单保持一致。
LANGUAGE_DISPLAY_NAMES = {
    "zh": ("Chinese", "中文"),
    "ja": ("Japanese", "日本語"),
    "en": ("English", "English"),
    "ko": ("Korean", "한국어"),
    "yue": ("Cantonese", "粤语"),
}

# CharacterConfig.human_name 的默认占位值；等于它时视为"未设置用户名"，不注入提示词
DEFAULT_HUMAN_NAME = "Human"


class ServiceContext:
    """Initializes, stores, and updates the asr, tts, and llm instances and other
    configurations for a connected client."""

    def __init__(self):
        self.config: Config = None
        self.system_config: SystemConfig = None
        self.character_config: CharacterConfig = None

        self.live2d_model: Live2dModel = None
        self.asr_engine: ASRInterface = None
        self.tts_engine: TTSInterface = None
        # 上次构建 TTS 引擎时使用的角色语言，用于检测语言变化并重建引擎
        self._tts_language: str = ""
        self.agent_engine: AgentInterface = None
        # translate_engine can be none if translation is disabled
        self.vad_engine: VADInterface | None = None
        self.translate_engine: TranslateInterface | None = None

        self.mcp_server_registery: ServerRegistry | None = None
        self.tool_adapter: ToolAdapter | None = None
        self.tool_manager: ToolManager | None = None
        self.mcp_client: MCPClient | None = None
        self.tool_executor: ToolExecutor | None = None

        # the system prompt is a combination of the persona prompt and live2d expression prompt
        self.system_prompt: str = None

        # Store the generated MCP prompt string (if MCP enabled)
        self.mcp_prompt: str = ""

        self.history_uid: str = ""  # Add history_uid field

        self.send_text: Callable = None
        self.client_uid: str = None

    def __str__(self):
        return (
            f"ServiceContext:\n"
            f"  System Config: {'Loaded' if self.system_config else 'Not Loaded'}\n"
            f"    Details: {json.dumps(self.system_config.model_dump(), indent=6) if self.system_config else 'None'}\n"
            f"  Live2D Model: {self.live2d_model.model_info if self.live2d_model else 'Not Loaded'}\n"
            f"  ASR Engine: {type(self.asr_engine).__name__ if self.asr_engine else 'Not Loaded'}\n"
            f"    Config: {json.dumps(self.character_config.asr_config.model_dump(), indent=6) if self.character_config.asr_config else 'None'}\n"
            f"  TTS Engine: {type(self.tts_engine).__name__ if self.tts_engine else 'Not Loaded'}\n"
            f"    Config: {json.dumps(self.character_config.tts_config.model_dump(), indent=6) if self.character_config.tts_config else 'None'}\n"
            f"  LLM Engine: {type(self.agent_engine).__name__ if self.agent_engine else 'Not Loaded'}\n"
            f"    Agent Config: {json.dumps(self.character_config.agent_config.model_dump(), indent=6) if self.character_config.agent_config else 'None'}\n"
            f"  VAD Engine: {type(self.vad_engine).__name__ if self.vad_engine else 'Not Loaded'}\n"
            f"    Agent Config: {json.dumps(self.character_config.vad_config.model_dump(), indent=6) if self.character_config.vad_config else 'None'}\n"
            f"  System Prompt: {self.system_prompt or 'Not Set'}\n"
            f"  MCP Enabled: {'Yes' if self.mcp_client else 'No'}"
        )

    # ==== Initializers

    async def _init_mcp_components(self, use_mcpp, enabled_servers):
        """Initializes MCP components based on configuration, dynamically fetching tool info."""
        logger.debug(
            f"Initializing MCP components: use_mcpp={use_mcpp}, enabled_servers={enabled_servers}"
        )

        # Reset MCP components first
        self.mcp_server_registery = None
        self.tool_manager = None
        self.mcp_client = None
        self.tool_executor = None
        self.json_detector = None
        self.mcp_prompt = ""

        if use_mcpp and enabled_servers:
            # 1. Initialize ServerRegistry
            self.mcp_server_registery = ServerRegistry()
            logger.info("ServerRegistry initialized or referenced.")

            # 2. Use ToolAdapter to get the MCP prompt and tools
            if not self.tool_adapter:
                logger.error(
                    "ToolAdapter not initialized before calling _init_mcp_components."
                )
                self.mcp_prompt = "[Error: ToolAdapter not initialized]"
                return  # Exit if ToolAdapter is mandatory and not initialized

            try:
                (
                    mcp_prompt_string,
                    openai_tools,
                    claude_tools,
                ) = await self.tool_adapter.get_tools(enabled_servers)
                # Store the generated prompt string
                self.mcp_prompt = mcp_prompt_string
                logger.info(
                    f"Dynamically generated MCP prompt string (length: {len(self.mcp_prompt)})."
                )
                logger.info(
                    f"Dynamically formatted tools - OpenAI: {len(openai_tools)}, Claude: {len(claude_tools)}."
                )

                # 3. Initialize ToolManager with the fetched formatted tools

                _, raw_tools_dict = await self.tool_adapter.get_server_and_tool_info(
                    enabled_servers
                )
                self.tool_manager = ToolManager(
                    formatted_tools_openai=openai_tools,
                    formatted_tools_claude=claude_tools,
                    initial_tools_dict=raw_tools_dict,
                )
                logger.info("ToolManager initialized with dynamically fetched tools.")

            except Exception as e:
                logger.error(
                    f"Failed during dynamic MCP tool construction: {e}", exc_info=True
                )
                # Ensure dependent components are not created if construction fails
                self.tool_manager = None
                self.mcp_prompt = "[Error constructing MCP tools/prompt]"

            # 4. Initialize MCPClient
            if self.mcp_server_registery:
                self.mcp_client = MCPClient(
                    self.mcp_server_registery, self.send_text, self.client_uid
                )
                logger.info("MCPClient initialized for this session.")
            else:
                logger.error(
                    "MCP enabled but ServerRegistry not available. MCPClient not created."
                )
                self.mcp_client = None  # Ensure it's None

            # 5. Initialize ToolExecutor
            if self.mcp_client and self.tool_manager:
                self.tool_executor = ToolExecutor(self.mcp_client, self.tool_manager)
                logger.info("ToolExecutor initialized for this session.")
            else:
                logger.warning(
                    "MCPClient or ToolManager not available. ToolExecutor not created."
                )
                self.tool_executor = None  # Ensure it's None

            logger.info("StreamJSONDetector initialized for this session.")

        elif use_mcpp and not enabled_servers:
            logger.warning(
                "use_mcpp is True, but mcp_enabled_servers list is empty. MCP components not initialized."
            )
        else:
            logger.debug(
                "MCP components not initialized (use_mcpp is False or no enabled servers)."
            )

    async def close(self):
        """Clean up resources, especially the MCPClient."""
        logger.info("Closing ServiceContext resources...")
        if self.mcp_client:
            logger.info(f"Closing MCPClient for context instance {id(self)}...")
            await self.mcp_client.aclose()
            self.mcp_client = None
        if self.agent_engine and hasattr(self.agent_engine, "close"):
            await self.agent_engine.close()  # Ensure agent resources are also closed
        logger.info("ServiceContext closed.")

    async def load_cache(
        self,
        config: Config,
        system_config: SystemConfig,
        character_config: CharacterConfig,
        live2d_model: Live2dModel,
        asr_engine: ASRInterface,
        tts_engine: TTSInterface,
        vad_engine: VADInterface,
        agent_engine: AgentInterface,
        translate_engine: TranslateInterface | None,
        mcp_server_registery: ServerRegistry | None = None,
        tool_adapter: ToolAdapter | None = None,
        send_text: Callable = None,
        client_uid: str = None,
    ) -> None:
        """
        Load the ServiceContext with the reference of the provided instances.
        Pass by reference so no reinitialization will be done.
        """
        if not character_config:
            raise ValueError("character_config cannot be None")
        if not system_config:
            raise ValueError("system_config cannot be None")

        self.config = config
        self.system_config = system_config
        self.character_config = character_config
        self.live2d_model = live2d_model
        self.asr_engine = asr_engine
        self.tts_engine = tts_engine
        self.vad_engine = vad_engine
        self.agent_engine = agent_engine
        self.translate_engine = translate_engine
        # Load potentially shared components by reference
        self.mcp_server_registery = mcp_server_registery
        self.tool_adapter = tool_adapter
        self.send_text = send_text
        self.client_uid = client_uid

        # Initialize session-specific MCP components
        await self._init_mcp_components(
            self.character_config.agent_config.agent_settings.basic_memory_agent.use_mcpp,
            self.character_config.agent_config.agent_settings.basic_memory_agent.mcp_enabled_servers,
        )

        logger.debug(f"Loaded service context with cache: {character_config}")

    async def load_from_config(self, config: Config) -> None:
        """
        Load the ServiceContext with the config.
        Reinitialize the instances if the config is different.

        Parameters:
        - config (Dict): The configuration dictionary.
        """
        if not self.config:
            self.config = config

        if not self.system_config:
            self.system_config = config.system_config

        if not self.character_config:
            self.character_config = config.character_config

        # update all sub-configs

        # init live2d from character config
        self.init_live2d(config.character_config.live2d_model_name)

        # init asr from character config
        self.init_asr(config.character_config.asr_config)

        # init tts from character config
        self.init_tts(
            config.character_config.tts_config,
            config.character_config.language,
        )

        # init vad from character config
        self.init_vad(config.character_config.vad_config)

        # Initialize shared ToolAdapter if it doesn't exist yet
        if (
            not self.tool_adapter
            and config.character_config.agent_config.agent_settings.basic_memory_agent.use_mcpp
        ):
            if not self.mcp_server_registery:
                logger.info(
                    "Initializing shared ServerRegistry within load_from_config."
                )
                self.mcp_server_registery = ServerRegistry()
            logger.info("Initializing shared ToolAdapter within load_from_config.")
            self.tool_adapter = ToolAdapter(server_registery=self.mcp_server_registery)

        # Initialize MCP Components before initializing Agent
        await self._init_mcp_components(
            config.character_config.agent_config.agent_settings.basic_memory_agent.use_mcpp,
            config.character_config.agent_config.agent_settings.basic_memory_agent.mcp_enabled_servers,
        )

        # init agent from character config
        await self.init_agent(
            config.character_config.agent_config,
            config.character_config.persona_prompt,
            config.character_config.language,
            config.character_config.human_name,
        )

        self.init_translate(
            config.character_config.tts_preprocessor_config.translator_config
        )

        # store typed config references
        self.config = config
        self.system_config = config.system_config or self.system_config
        self.character_config = config.character_config

    def init_live2d(self, live2d_model_name: str) -> None:
        logger.info(f"Initializing Live2D: {live2d_model_name}")
        try:
            self.live2d_model = Live2dModel(live2d_model_name)
            self.character_config.live2d_model_name = live2d_model_name
        except Exception as e:
            logger.critical(f"Error initializing Live2D: {e}")
            logger.critical("Try to proceed without Live2D...")

    async def switch_live2d_model(self, model_name: str) -> None:
        """Switch only the visual/emotion model; preserve character, engines, agent memory.

        Only BasicMemoryAgent exposes the two public capabilities used here
        (set_live2d_model / set_system); other agents are rejected outright.
        """
        if self.live2d_model.live2d_model_name == model_name:
            return

        # 先构造候选：失败时旧模型、旧提示词完全不变
        candidate = Live2dModel(model_name)

        agent = self.agent_engine
        if agent is None:
            raise RuntimeError("agent is not initialized")
        if not callable(getattr(agent, "set_live2d_model", None)):
            raise RuntimeError("current agent does not support Live2D model switching")
        if not callable(getattr(agent, "set_system", None)):
            raise RuntimeError("current agent does not support system prompt refresh")

        # construct_system_prompt 从 self.live2d_model 读 emotionMap，故为构建候选 prompt 临时替换
        old_model = self.live2d_model
        old_model_name = self.character_config.live2d_model_name
        old_system_prompt = self.system_prompt
        self.live2d_model = candidate
        self.character_config.live2d_model_name = model_name
        try:
            prompt = await self.construct_system_prompt(
                self.character_config.persona_prompt,
                self.character_config.language,
                self.character_config.human_name,
            )
            agent.set_live2d_model(
                candidate
            )  # 重建 decorators，绑定 candidate emotionMap
            agent.set_system(prompt)  # 走 setter 以保留 interrupt 提示语义
        except Exception:
            # 精确回滚：context 字段、agent 模型闭包与 agent 系统提示一并复位。
            # 二次失败只记录日志，不覆盖原异常。
            try:
                agent.set_live2d_model(old_model)
                agent.set_system(old_system_prompt)
            except Exception:
                logger.exception(
                    "Failed to roll back agent after Live2D switch failure"
                )
            self.live2d_model = old_model
            self.character_config.live2d_model_name = old_model_name
            self.system_prompt = old_system_prompt
            raise

        self.system_prompt = prompt  # 仅在所有步骤成功后提交，避免半套状态对外可见
        logger.info(
            f"Switched Live2D model: {old_model.live2d_model_name} -> {model_name}"
        )

    def init_asr(self, asr_config: ASRConfig) -> None:
        # 与 init_vad 一致：asr_model 为 None 表示禁用，不做任何初始化。
        # 注意这里必须先返回，否则下面的 getattr(cfg, None) 会抛 TypeError。
        if asr_config.asr_model is None:
            logger.info("ASR is disabled.")
            self.asr_engine = None
            self.character_config.asr_config = asr_config
            return

        if not self.asr_engine or (self.character_config.asr_config != asr_config):
            logger.info(f"Initializing ASR: {asr_config.asr_model}")
            self.asr_engine = ASRFactory.get_asr_system(
                asr_config.asr_model,
                **getattr(asr_config, asr_config.asr_model).model_dump(),
            )
            # saving config should be done after successful initialization
            self.character_config.asr_config = asr_config
        else:
            logger.info("ASR already initialized with the same config.")

    def init_tts(self, tts_config: TTSConfig, language: str = "") -> None:
        """(Re)initialize TTS.

        ``language`` 必须显式传入：load_from_config 里 self.character_config 是在
        最后才赋值的，本方法执行时它还是上一次的配置。
        角色语言会覆盖引擎配置里的 text_lang（若该引擎有此参数），
        但不覆盖 prompt_lang —— 那是参考音频的语言，属于声音模型的属性。
        """
        engine_cfg_obj = getattr(tts_config, tts_config.tts_model.lower())
        engine_cfg = engine_cfg_obj.model_dump() if engine_cfg_obj is not None else {}
        role_lang = (language or "").strip().lower()
        if role_lang in ("", "auto"):
            role_lang = ""
        if role_lang and "text_lang" in engine_cfg:
            if engine_cfg.get("text_lang") != role_lang:
                logger.info(
                    f"Overriding TTS text_lang with the character language: "
                    f"{engine_cfg.get('text_lang')!r} -> {role_lang!r}"
                )
            engine_cfg["text_lang"] = role_lang

        # language 变化也要触发重建，否则只改语言不会生效
        changed = (
            not self.tts_engine
            or self.character_config.tts_config != tts_config
            or self._tts_language != role_lang
        )
        if changed:
            logger.info(f"Initializing TTS: {tts_config.tts_model}")
            self.tts_engine = TTSFactory.get_tts_engine(
                tts_config.tts_model,
                **engine_cfg,
            )
            # saving config should be done after successful initialization
            self.character_config.tts_config = tts_config
            self._tts_language = role_lang
        else:
            logger.info("TTS already initialized with the same config.")

    def init_vad(self, vad_config: VADConfig) -> None:
        if vad_config.vad_model is None:
            logger.info("VAD is disabled.")
            self.vad_engine = None
            return

        if not self.vad_engine or (self.character_config.vad_config != vad_config):
            logger.info(f"Initializing VAD: {vad_config.vad_model}")
            self.vad_engine = VADFactory.get_vad_engine(
                vad_config.vad_model,
                **getattr(vad_config, vad_config.vad_model.lower()).model_dump(),
            )
            # saving config should be done after successful initialization
            self.character_config.vad_config = vad_config
        else:
            logger.info("VAD already initialized with the same config.")

    async def init_agent(
        self,
        agent_config: AgentConfig,
        persona_prompt: str,
        language: str = "",
        human_name: str = "",
    ) -> None:
        """Initialize or update the LLM engine based on agent configuration.

        ``language`` / ``human_name`` 需显式传入：本方法在 load_from_config 里执行时，
        self.character_config 还是上一次的配置（它在最后才被替换）。
        """
        logger.info(f"Initializing Agent: {agent_config.conversation_agent_choice}")

        if (
            self.agent_engine is not None
            and agent_config == self.character_config.agent_config
            and persona_prompt == self.character_config.persona_prompt
            and (language or "") == (self.character_config.language or "")
            and (human_name or "") == (self.character_config.human_name or "")
        ):
            logger.debug("Agent already initialized with the same config.")
            return

        system_prompt = await self.construct_system_prompt(
            persona_prompt, language, human_name
        )

        # Pass avatar to agent factory
        avatar = self.character_config.avatar or ""  # Get avatar from config

        try:
            self.agent_engine = AgentFactory.create_agent(
                conversation_agent_choice=agent_config.conversation_agent_choice,
                agent_settings=agent_config.agent_settings.model_dump(),
                llm_configs=agent_config.llm_configs.model_dump(),
                system_prompt=system_prompt,
                live2d_model=self.live2d_model,
                tts_preprocessor_config=self.character_config.tts_preprocessor_config,
                character_avatar=avatar,
                system_config=self.system_config.model_dump(),
                tool_manager=self.tool_manager,
                tool_executor=self.tool_executor,
                mcp_prompt_string=self.mcp_prompt,
            )

            logger.debug(f"Agent choice: {agent_config.conversation_agent_choice}")
            logger.debug(f"System prompt: {system_prompt}")

            # Save the current configuration
            self.character_config.agent_config = agent_config
            self.system_prompt = system_prompt

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise

    def init_translate(self, translator_config: TranslatorConfig) -> None:
        """Initialize or update the translation engine based on the configuration."""

        if not translator_config.translate_audio:
            logger.debug("Translation is disabled.")
            return

        if (
            not self.translate_engine
            or self.character_config.tts_preprocessor_config.translator_config
            != translator_config
        ):
            logger.info(
                f"Initializing Translator: {translator_config.translate_provider}"
            )
            self.translate_engine = TranslateFactory.get_translator(
                translator_config.translate_provider,
                getattr(
                    translator_config, translator_config.translate_provider
                ).model_dump(),
            )
            self.character_config.tts_preprocessor_config.translator_config = (
                translator_config
            )
        else:
            logger.info("Translation already initialized with the same config.")

    # ==== utils

    async def construct_system_prompt(
        self, persona_prompt: str, language: str = "", human_name: str = ""
    ) -> str:
        """
        Append tool prompts to persona prompt.

        Parameters:
        - persona_prompt (str): The persona prompt.
        - language (str): 角色语言代码；显式传入以保证在 load_from_config
          执行期间拿到的是**新**配置的语言（此时 self.character_config 尚未替换）。
        - human_name (str): 用户的名字，同样需显式传入（理由同上）。用于在提示词里
          告诉 LLM 该怎么称呼用户 —— 否则该配置项完全不起作用。

        Returns:
        - str: The system prompt with all tool prompts appended.
        """
        logger.debug(f"constructing persona_prompt: '''{persona_prompt}'''")

        # 放最前面的都是"身份/硬约束"类指令，优先级高于人设正文
        directives = []
        user_directive = self._user_directive(human_name)
        if user_directive:
            directives.append(user_directive)
        language_directive = self._language_directive(language)
        if language_directive:
            directives.append(language_directive)
        if directives:
            persona_prompt = "\n\n".join(directives) + "\n\n" + persona_prompt

        for prompt_name, prompt_file in self.system_config.tool_prompts.items():
            if (
                prompt_name == "group_conversation_prompt"
                or prompt_name == "proactive_speak_prompt"
            ):
                continue

            prompt_content = prompt_loader.load_util(prompt_file)

            if prompt_name == "live2d_expression_prompt":
                if not self.live2d_model or not self.live2d_model.emo_map:
                    # 模型没有可用的表情映射：注入空关键词列表只会诱导 LLM 编造
                    # [curiosity] 之类的未注册关键词（漏进字幕），直接跳过该提示词
                    continue
                prompt_content = prompt_content.replace(
                    "[<insert_emomap_keys>]", self.live2d_model.emo_str
                )

            if prompt_name == "mcp_prompt":
                continue

            persona_prompt += prompt_content

        logger.debug("\n === System Prompt ===")
        logger.debug(persona_prompt)

        return persona_prompt

    def _user_directive(self, human_name: str = "") -> str:
        """Build the "the user is called X" instruction.

        返回空串表示不注入：human_name 为空、或仍是默认占位值 "Human" 时都没必要
        往提示词里塞噪音。语言来源优先级：显式传入 > self.character_config.human_name。
        """
        name = (human_name or "").strip()
        if not name:
            name = (self.character_config.human_name or "").strip()
        if not name or name.lower() == DEFAULT_HUMAN_NAME.lower():
            return ""
        return (
            "[User]\n"
            f'You are talking with a user named "{name}". '
            "Address them by this name when appropriate."
        )

    def _language_directive(self, language: str = "") -> str:
        """Build the "always reply in <language>" instruction.

        Returns an empty string when there is no language restriction.
        语言来源优先级：显式传入的 language > self.character_config.language。
        """
        lang = (language or "").strip().lower()
        if not lang:
            lang = (self.character_config.language or "").strip().lower()
        if not lang or lang == "auto":
            return ""
        name = LANGUAGE_DISPLAY_NAMES.get(lang)
        if not name:
            return ""
        return (
            "[Language Requirement]\n"
            f"Always reply in {name[0]} ({name[1]}), regardless of the language "
            "the user writes in.\n"
            "Do not use any other language in your replies."
        )

    async def handle_config_switch(
        self,
        websocket: WebSocket,
        config_file_name: str,
    ) -> None:
        """
        Handle the configuration switch request.
        Change the configuration to a new config and notify the client.

        Parameters:
        - websocket (WebSocket): The WebSocket connection.
        - config_file_name (str): The name of the configuration file.
        """
        try:
            new_character_config_data = None

            if config_file_name == "conf.yaml":
                # Load base config。
                # 同样套用 default_character 指针，这样 Web UI 切回「基础配置」时
                # 得到的仍是启动器设定的默认角色，而不是 conf.yaml 自带的那个。
                new_character_config_data = apply_default_character(
                    read_yaml("conf.yaml")
                ).get("character_config")
            else:
                # Load alternative config and merge with base config
                characters_dir = self.system_config.config_alts_dir
                file_path = os.path.normpath(
                    os.path.join(characters_dir, config_file_name)
                )
                if not file_path.startswith(characters_dir):
                    raise ValueError("Invalid configuration file path")

                alt_config_data = read_yaml(file_path).get("character_config")

                # 合并底是 conf.yaml 自身的 character_config，不套默认角色指针：
                # 以当前角色或默认角色为底，都会把该角色独有的可选键
                # （live2d_model_names、tts_config 等）残留给目标角色
                base_character_data = read_yaml("conf.yaml").get("character_config")
                new_character_config_data = deep_merge(
                    base_character_data, alt_config_data
                )

            if new_character_config_data:
                new_config = {
                    "system_config": self.system_config.model_dump(),
                    "character_config": new_character_config_data,
                }
                new_config = validate_config(new_config)
                await self.load_from_config(new_config)  # Await the async load
                logger.debug(f"New config: {self}")
                logger.debug(
                    f"New character config: {self.character_config.model_dump()}"
                )

                # Send responses to client
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "set-model-and-conf",
                            "model_info": self.live2d_model.model_info,
                            # 键名 conf_name 是前端的历史包袱，值即角色显示名
                            "conf_name": self.character_config.character_name,
                            "conf_uid": self.character_config.conf_uid,
                        }
                    )
                )

                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "config-switched",
                            "message": f"Switched to config: {config_file_name}",
                        }
                    )
                )

                logger.info(f"Configuration switched to {config_file_name}")
            else:
                raise ValueError(
                    f"Failed to load configuration from {config_file_name}"
                )

        except Exception as e:
            logger.error(f"Error switching configuration: {e}")
            logger.debug(self)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Error switching configuration: {str(e)}",
                    }
                )
            )
            raise e


def deep_merge(dict1, dict2):
    """
    Recursively merges dict2 into dict1, prioritizing values from dict2.
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
