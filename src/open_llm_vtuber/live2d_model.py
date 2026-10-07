import json
from pathlib import Path

import chardet
from loguru import logger

# This class will only prepare the payload for the live2d model
# the process of sending the payload should be done by the caller
# This class is **Not responsible** for sending the payload to the server


class Live2dModel:
    """
    A class to represent a Live2D model. This class only prepares and stores the information of the Live2D model. It does not send anything to the frontend or server or anything.

    Attributes:
        model_dict_path (str): The path to the model dictionary file.
        live2d_model_name (str): The name of the Live2D model.
        model_info (dict): The information of the Live2D model.
        emo_map (dict): The emotion map of the Live2D model.
        emo_str (str): The string representation of the emotion map of the Live2D model.
    """

    model_dict_path: str
    live2d_model_name: str
    model_info: dict
    emo_map: dict
    emo_str: str

    def __init__(
        self, live2d_model_name: str, model_dict_path: str = "model_dict.json"
    ):
        self.model_dict_path: str = model_dict_path
        self.live2d_model_name: str = live2d_model_name
        self.set_model(live2d_model_name)

    def set_model(self, model_name: str) -> None:
        """
        Set the model with its name and load the model information. This method will initialize the `self.model_info`, `self.emo_map`, and `self.emo_str` attributes.
        This method is called in the constructor.

        Parameters:
            model_name (str): The name of the live2d model.

            Returns:
            None
        """

        self.model_info: dict = self._lookup_model_info(model_name)
        self.emo_map: dict = {
            k.lower(): v for k, v in self.model_info["emotionMap"].items()
        }
        self.emo_str: str = " ".join([f"[{key}]," for key in self.emo_map.keys()])
        # emo_str is a string of the keys in the emoMap dictionary. The keys are enclosed in square brackets.
        # example: `"[fear], [anger], [disgust], [sadness], [joy], [neutral], [surprise]"`

    @staticmethod
    def _load_file_content(file_path: str) -> str:
        """Load the content of a file with robust encoding handling."""
        # Try common encodings first
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "ascii"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue

        # If all common encodings fail, try to detect encoding
        try:
            with open(file_path, "rb") as file:
                raw_data = file.read()
            detected = chardet.detect(raw_data)
            detected_encoding = detected["encoding"]

            if detected_encoding:
                try:
                    return raw_data.decode(detected_encoding)
                except UnicodeDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Error detecting encoding for {file_path}: {e}")

        raise UnicodeError(f"Failed to decode {file_path} with any encoding")

    def _lookup_model_info(self, model_name: str) -> dict:
        """
        Find the model information from the model dictionary and return the information about the matched model.

        Parameters:
            model_name (str): The name of the live2d model.

        Returns:
            dict: The dictionary with the information of the matched model.

        Raises:
            FileNotFoundError if the model dictionary file is not found.

            json.JSONDecodeError if the model dictionary file is not a valid JSON file.

            KeyError if the model name is not found in the model dictionary.

        """

        self.live2d_model_name = model_name

        model_dict = load_model_dict(self.model_dict_path)

        # Find the model in the model_dict
        matched_model = next(
            (model for model in model_dict if model["name"] == model_name), None
        )

        if matched_model is None:
            logger.critical(f"Unable to find {model_name} in {self.model_dict_path}.")
            raise KeyError(
                f"{model_name} not found in model dictionary {self.model_dict_path}."
            )

        # The feature: "translate model url to full url if it starts with '/' " is no longer implemented here

        logger.info("Model Information Loaded.")

        return matched_model

    @staticmethod
    def list_frontend_models(
        model_dict_path: str = "model_dict.json",
    ) -> list[dict[str, str]]:
        """Return public Live2D selector entries; exclude Spine/malformed records."""

        raw = load_model_dict(model_dict_path)

        if not isinstance(raw, list):
            raise ValueError("model_dict.json must be a list")

        result: list[dict[str, str]] = []
        for info in raw:
            if not isinstance(info, dict):
                continue
            name = info.get("name")
            url = info.get("url")
            if (
                isinstance(name, str)
                and isinstance(url, str)
                and not url.endswith(".skel")
            ):
                result.append({"name": name})
        return result

    def extract_emotion(self, str_to_check: str) -> list:
        """
        Check the input string for any emotion keywords and return a list of values (the expression index) of the emotions found in the string.

        Parameters:
            str_to_check (str): The string to check for emotions.

        Returns:
            list: A list of values of the emotions found in the string. An empty list is returned if no emotions are found.
        """

        expression_list = []
        str_to_check = str_to_check.lower()

        i = 0
        while i < len(str_to_check):
            if str_to_check[i] != "[":
                i += 1
                continue
            for key in self.emo_map.keys():
                emo_tag = f"[{key}]"
                if str_to_check[i : i + len(emo_tag)] == emo_tag:
                    expression_list.append(self.emo_map[key])
                    i += len(emo_tag) - 1
                    break
            i += 1
        return expression_list

    def remove_emotion_keywords(self, target_str: str) -> str:
        """
        Remove the emotion keywords from the input string and return the cleaned string.

        Parameters:
            str_to_check (str): The string to check for emotions.

        Returns:
            str: The cleaned string with the emotion keywords removed.
        """

        lower_str = target_str.lower()

        for key in self.emo_map.keys():
            lower_key = f"[{key}]".lower()
            while lower_key in lower_str:
                start_index = lower_str.find(lower_key)
                end_index = start_index + len(lower_key)
                target_str = target_str[:start_index] + target_str[end_index:]
                lower_str = lower_str[:start_index] + lower_str[end_index:]
        return target_str


def resolve_model_dict_path(model_dict_path: str = "model_dict.json") -> str:
    """active 登记表路径：同名兄弟文件 <stem>.local<suffix> 存在即整份取代基准。
    公开克隆无 local 文件 → 基准即 active。本规则为唯一权威，
    scripts/scan_live2d_models.py · fit_live2d_scale.py · launcher 为脚本/独立
    venv 场景的内联副本（各文件注释互指）。"""
    path = Path(model_dict_path)
    local_sibling = path.with_name(f"{path.stem}.local{path.suffix}")
    if local_sibling.is_file():
        return str(local_sibling)
    return model_dict_path


def load_model_dict(model_dict_path: str = "model_dict.json") -> list[dict]:
    """读 active 登记表并解析；错误语义（logger.critical + 原样 raise
    FileNotFoundError/JSONDecodeError/UnicodeError）沿用 _lookup_model_info
    原读段；非 list 抛 ValueError。"""
    active_path = resolve_model_dict_path(model_dict_path)

    try:
        file_content = Live2dModel._load_file_content(active_path)
        raw = json.loads(file_content)
    except FileNotFoundError as file_e:
        logger.critical(f"Model dictionary file not found at {active_path}.")
        raise file_e
    except json.JSONDecodeError as json_e:
        logger.critical(
            f"Error decoding JSON from model dictionary file at {active_path}."
        )
        raise json_e
    except UnicodeError as uni_e:
        logger.critical(f"Error reading model dictionary file at {active_path}.")
        raise uni_e
    except Exception as e:
        logger.critical(
            f"Error occurred while reading model dictionary file at {active_path}."
        )
        raise e

    if not isinstance(raw, list):
        raise ValueError(f"model dictionary file at {active_path} must be a list")

    return raw
