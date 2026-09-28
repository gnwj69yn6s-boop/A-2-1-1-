import os
import json
import base64

import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

# ============================================================
# 1. 환경 변수 및 API 설정
# ============================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ============================================================
# matplotlib 한글 폰트 설정
# ============================================================

def set_korean_font():
    """
    matplotlib에서 한글이 정상적으로 표시되도록
    Windows의 맑은 고딕 폰트를 설정한다.
    """

    font_paths = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf"
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            font_name = font_manager.FontProperties(
                fname=font_path
            ).get_name()

            rc("font", family=font_name)
            plt.rcParams["axes.unicode_minus"] = False

            return

    print("[경고] 한글 폰트를 찾지 못했습니다.")



# ============================================================
# 2. 사용자 입력
# ============================================================

def get_user_input():
    print("=" * 60)
    print("             브랜드 아이덴티티 생성기")
    print("=" * 60)

    print("\n사용할 AI를 선택하세요.")
    print("1. OpenAI")
    print("2. Google Gemini")

    while True:
        ai_choice = input("선택: ").strip()

        if ai_choice in ["1", "2"]:
            break

        print("1 또는 2를 입력해주세요.")

    brief_path = input(
        "\n브랜드 브리프 JSON 파일 경로 "
        "(기본값: ./brand_brief.json): "
    ).strip()

    if not brief_path:
        brief_path = "./brand_brief.json"

    output_dir = input(
        "출력 폴더 경로 (기본값: ./output): "
    ).strip()

    if not output_dir:
        output_dir = "./output"

    return ai_choice, brief_path, output_dir


# ============================================================
# 3. API 클라이언트 생성
# ============================================================

def create_client(ai_choice):
    if ai_choice == "1":
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다.\n"
                ".env 파일을 확인해주세요."
            )

        return OpenAI(api_key=OPENAI_API_KEY)

    if ai_choice == "2":
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY가 설정되지 않았습니다.\n"
                ".env 파일을 확인해주세요."
            )

        return genai.Client(api_key=GEMINI_API_KEY)

    raise ValueError("잘못된 AI 선택입니다.")


# ============================================================
# 4. 브랜드 브리프 로드 및 검증
# ============================================================

def load_brief(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"브리프 파일을 찾을 수 없습니다: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        brief = json.load(file)

    required_fields = [
        "industry",
        "target",
        "keywords"
    ]

    for field in required_fields:
        if field not in brief:
            raise ValueError(
                f"필수 필드가 없습니다: {field}"
            )

    if not isinstance(brief["keywords"], list):
        raise ValueError(
            "keywords는 리스트 형식이어야 합니다."
        )

    return brief


# ============================================================
# 5. LLM 호출
# ============================================================

def call_llm(ai_choice, client, prompt):
    if ai_choice == "1":
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )

        return response.output_text

    if ai_choice == "2":
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text

    raise ValueError("지원하지 않는 AI입니다.")


# ============================================================
# 6. JSON 응답 변환
# ============================================================

def parse_json_response(response_text):
    text = response_text.strip()

    # ```json ... ``` 형식 제거
    if text.startswith("```"):
        lines = text.splitlines()

        if len(lines) >= 3:
            text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            return json.loads(
                text[start:end + 1]
            )

        raise ValueError(
            "AI 응답을 JSON으로 변환할 수 없습니다."
        )


# ============================================================
# 7. 브랜드 네이밍 생성
# ============================================================

def generate_names(ai_choice, client, brief):
    prompt = f"""
당신은 전문 브랜드 네이밍 전문가입니다.

다음 브랜드 브리프를 분석하여
브랜드명 후보 3~5개를 만들어주세요.

[브랜드 브리프]
업종: {brief["industry"]}
타겟: {brief["target"]}
키워드: {brief["keywords"]}
톤앤매너: {brief.get("tone", "")}
경쟁사: {brief.get("competitors", [])}
추가 요청사항: {brief.get("notes", "")}

각 브랜드명에는 의미와 네이밍 이유를 작성해주세요.

반드시 다음 JSON 형식만 반환하세요.

{{
    "brand_names": [
        {{
            "name": "브랜드명",
            "meaning": "이름의 의미",
            "reason": "이 이름을 추천하는 이유"
        }}
    ]
}}
"""

    response = call_llm(
        ai_choice,
        client,
        prompt
    )

    return parse_json_response(response)


# ============================================================
# 8. 슬로건 생성
# ============================================================

def generate_slogans(ai_choice, client, brief):
    prompt = f"""
당신은 전문 브랜드 카피라이터입니다.

다음 브랜드를 위한 슬로건/태그라인 3개를 만들어주세요.

업종: {brief["industry"]}
타겟: {brief["target"]}
키워드: {brief["keywords"]}
톤앤매너: {brief.get("tone", "")}
추가 요청사항: {brief.get("notes", "")}

짧고 기억하기 쉬우며 브랜드의 특징이 드러나야 합니다.

반드시 다음 JSON 형식만 반환하세요.

{{
    "slogans": [
        "슬로건 1",
        "슬로건 2",
        "슬로건 3"
    ]
}}
"""

    response = call_llm(
        ai_choice,
        client,
        prompt
    )

    return parse_json_response(response)


# ============================================================
# 9. 브랜드 스토리 생성
# ============================================================

def generate_story(ai_choice, client, brief):
    prompt = f"""
당신은 전문 브랜드 스토리텔러입니다.

다음 브랜드의 브랜드 스토리를 약 300자로 작성해주세요.

반드시 다음 내용을 포함하세요.

1. 브랜드의 탄생 배경
2. 브랜드 철학
3. 브랜드가 추구하는 비전

업종: {brief["industry"]}
타겟: {brief["target"]}
키워드: {brief["keywords"]}
톤앤매너: {brief.get("tone", "")}
경쟁사: {brief.get("competitors", [])}
추가 요청사항: {brief.get("notes", "")}

반드시 다음 JSON 형식만 반환하세요.

{{
    "brand_story": "약 300자의 브랜드 스토리"
}}
"""

    response = call_llm(
        ai_choice,
        client,
        prompt
    )

    return parse_json_response(response)


# ============================================================
# 10. 컬러 팔레트 생성
# ============================================================

def generate_palette(ai_choice, client, brief):
    prompt = f"""
당신은 전문 브랜드 디자이너입니다.

다음 브랜드에 어울리는 컬러 팔레트를 추천해주세요.

업종: {brief["industry"]}
타겟: {brief["target"]}
키워드: {brief["keywords"]}
톤앤매너: {brief.get("tone", "")}
추가 요청사항: {brief.get("notes", "")}

조건:
- 메인 컬러 1개
- 서브 컬러 2~3개
- 모든 색상은 HEX 코드
- 브랜드 이미지와 어울리는 이유도 간단하게 설명

반드시 다음 JSON 형식만 반환하세요.

{{
    "main": {{
        "name": "색상 이름",
        "hex": "#000000",
        "reason": "추천 이유"
    }},
    "sub": [
        {{
            "name": "색상 이름",
            "hex": "#000000",
            "reason": "추천 이유"
        }}
    ]
}}
"""

    response = call_llm(
        ai_choice,
        client,
        prompt
    )

    return parse_json_response(response)


# ============================================================
# 11. 컬러 팔레트 PNG 생성
# ============================================================

def save_palette_image(palette, output_path):
    colors = [
        palette["main"]
    ] + palette["sub"]

    fig, ax = plt.subplots(
        figsize=(10, 3)
    )

    for index, color in enumerate(colors):
        ax.add_patch(
            plt.Rectangle(
                (index, 0),
                1,
                1,
                color=color["hex"]
            )
        )

        ax.text(
            index + 0.5,
            0.5,
            f'{color["name"]}\n{color["hex"]}',
            ha="center",
            va="center",
            fontsize=10
        )

    ax.set_xlim(
        0,
        len(colors)
    )

    ax.set_ylim(
        0,
        1
    )

    ax.axis("off")

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# 12. 로고 생성
# ============================================================

def generate_logos(ai_choice, client, brief, output_dir):
    for index in range(1, 4):
        print(
            f"  로고 시안 {index}/3 생성 중..."
        )

        try:
            prompt = f"""
Create a professional logo concept.

Brand industry:
{brief["industry"]}

Target audience:
{brief["target"]}

Keywords:
{brief["keywords"]}

Brand tone:
{brief.get("tone", "")}

Additional requirements:
{brief.get("notes", "")}

Create a clean, memorable,
professional commercial logo.

Use a simple background.
Avoid unnecessary decorative elements.
"""

            if ai_choice == "1":
                result = client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    size="1024x1024"
                )

                image_data = base64.b64decode(
                    result.data[0].b64_json
                )

            else:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=prompt
                )

                image_data = None

                for part in response.parts:
                    if part.inline_data is not None:
                        image_data = part.inline_data.data
                        break

                if image_data is None:
                    raise ValueError(
                        "Gemini에서 이미지 데이터를 받지 못했습니다."
                    )

            output_path = os.path.join(
                output_dir,
                f"logo_{index:02d}.png"
            )

            with open(
                output_path,
                "wb"
            ) as file:
                file.write(image_data)

            print(
                f"  ✓ logo_{index:02d}.png 저장 완료"
            )

        except Exception as error:
            print(
                f"  ✗ 로고 {index} 생성 실패: {error}"
            )


# ============================================================
# 13. 결과 JSON 저장
# ============================================================

def save_result(result, output_dir):
    output_path = os.path.join(
        output_dir,
        "brand_result.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"✓ 결과 저장: {output_path}"
    )


# ============================================================
# 14. 메인 프로그램
# ============================================================

def main():

    set_korean_font()

    # 사용자 입력
    ai_choice, brief_path, output_dir = get_user_input()

    # 출력 폴더 생성
    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # API 클라이언트
    try:
        client = create_client(
            ai_choice
        )

    except Exception as error:
        print(
            f"\n[오류] API 설정 오류\n{error}"
        )
        return

    # 브랜드 브리프 로드
    try:
        brief = load_brief(
            brief_path
        )

    except Exception as error:
        print(
            f"\n[오류] 브랜드 브리프 오류\n{error}"
        )
        return

    print("\n브랜드 브리프를 불러왔습니다.")
    print(
        f"업종: {brief['industry']}"
    )
    print(
        f"타겟: {brief['target']}"
    )
    print(
        f"키워드: {', '.join(brief['keywords'])}"
    )

    result = {}

    # --------------------------------------------------------
    # 네이밍
    # --------------------------------------------------------

    print("\n[1/5] 브랜드 네이밍 생성")

    try:
        result["brand_names"] = generate_names(
            ai_choice,
            client,
            brief
        )

        print("✓ 네이밍 생성 완료")

    except Exception as error:
        print(
            f"✗ 네이밍 생성 실패: {error}"
        )

        result["brand_names"] = None

    # --------------------------------------------------------
    # 슬로건
    # --------------------------------------------------------

    print("\n[2/5] 슬로건 생성")

    try:
        result["slogans"] = generate_slogans(
            ai_choice,
            client,
            brief
        )

        print("✓ 슬로건 생성 완료")

    except Exception as error:
        print(
            f"✗ 슬로건 생성 실패: {error}"
        )

        result["slogans"] = None

    # --------------------------------------------------------
    # 브랜드 스토리
    # --------------------------------------------------------

    print("\n[3/5] 브랜드 스토리 생성")

    try:
        result["brand_story"] = generate_story(
            ai_choice,
            client,
            brief
        )

        print("✓ 브랜드 스토리 생성 완료")

    except Exception as error:
        print(
            f"✗ 브랜드 스토리 생성 실패: {error}"
        )

        result["brand_story"] = None

    # --------------------------------------------------------
    # 컬러 팔레트
    # --------------------------------------------------------

    print("\n[4/5] 컬러 팔레트 생성")

    try:
        palette_result = generate_palette(
            ai_choice,
            client,
            brief
        )

        result["color_palette"] = palette_result

        save_palette_image(
            palette_result,
            os.path.join(
                output_dir,
                "color_palette.png"
            )
        )

        print(
            "✓ 컬러 팔레트 PNG 저장 완료"
        )

    except Exception as error:
        print(
            f"✗ 컬러 팔레트 생성 실패: {error}"
        )

        result["color_palette"] = None

    # --------------------------------------------------------
    # 로고
    # --------------------------------------------------------

    print("\n[5/5] 로고 시안 생성")

    generate_logos(
        ai_choice,
        client,
        brief,
        output_dir
    )

    result["logo_files"] = [
        "logo_01.png",
        "logo_02.png",
        "logo_03.png"
    ]

    # --------------------------------------------------------
    # 결과 저장
    # --------------------------------------------------------

    save_result(
        result,
        output_dir
    )

    # --------------------------------------------------------
    # 종료
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("브랜드 아이덴티티 생성이 완료되었습니다.")
    print(f"결과 폴더: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
