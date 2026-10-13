"""CSS 스타일을 분석하여 숨겨진 광고 요소를 탐지한다."""

import re


def parse_style(style):
    """CSS 문자열 또는 딕셔너리를 분석하기 쉬운 형태로 변환한다."""

    if isinstance(style, dict):
        return {
            str(key).strip().lower(): str(value).strip().lower()
            for key, value in style.items()
        }

    if not isinstance(style, str):
        return {}

    result = {}

    for declaration in style.split(";"):
        if ":" not in declaration:
            continue

        key, value = declaration.split(":", 1)
        result[key.strip().lower()] = value.strip().lower()

    return result


def detect_transparent(style):
    """투명하게 숨긴 요소인지 확인한다."""

    css = parse_style(style)

    opacity = css.get("opacity", "1")

    try:
        if float(opacity) == 0:
            return True
    except ValueError:
        pass

    color = re.sub(r"\s+", "", css.get("color", ""))

    if color in {
        "transparent",
        "rgba(0,0,0,0)",
        "rgba(255,255,255,0)",
    }:
        return True

    return False


def detect_offscreen(style):
    """화면 바깥으로 이동시킨 요소인지 확인한다."""

    css = parse_style(style)

    position = css.get("position", "")

    if position not in {"absolute", "fixed"}:
        return False

    for property_name in ("left", "right", "top", "bottom"):
        value = css.get(property_name, "")

        match = re.fullmatch(
            r"(-?\d+(?:\.\d+)?)(px|rem|em|vw|vh)?",
            value,
        )

        if match:
            number = float(match.group(1))

            if number <= -1000:
                return True

    return False


def detect_hidden_css(style):
    """CSS 은닉 기법을 모두 확인한다."""

    css = parse_style(style)
    techniques = []

    if detect_transparent(css):
        techniques.append("TRANSPARENT")

    if detect_offscreen(css):
        techniques.append("OFFSCREEN")

    if css.get("visibility") == "hidden":
        techniques.append("VISIBILITY_HIDDEN")

    if css.get("display") == "none":
        techniques.append("DISPLAY_NONE")

    return techniques