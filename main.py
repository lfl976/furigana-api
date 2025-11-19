from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sudachipy import tokenizer, dictionary
import jaconv
import re
from typing import List, Optional

app = FastAPI()

# 1. 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 初始化 Sudachi
try:
    tokenizer_obj = dictionary.Dictionary().create()
    mode = tokenizer.Tokenizer.SplitMode.C 
except Exception as e:
    print(f"Sudachi 初始化失败: {e}")
    raise e

# --- 数据模型定义 ---

class FuriganaRequest(BaseModel):
    text: str

# 定义单个词的返回结构
class TokenData(BaseModel):
    surface: str                # 原文，如 "食べ" 或 "私"
    reading: str                # 平假名读音，如 "たべ" 或 "わたし"
    # 以下字段仅在有汉字且需要注音时存在
    kanji_base: Optional[str] = None  # 需要注音的汉字部分，如 "食"
    furigana: Optional[str] = None    # 对应的注音，如 "た"
    okurigana: Optional[str] = None   # 不需要注音的尾部送假名，如 "べ"

# 定义 JSON 接口的返回结构
class AnalysisResponse(BaseModel):
    results: List[TokenData]


# --- 3. 核心逻辑：仅做分析，不拼接 HTML ---
def analyze_text_logic(text: str) -> List[TokenData]:
    tokens = tokenizer_obj.tokenize(text, mode)
    results = []

    for token in tokens:
        surface = token.surface()       
        reading_kata = token.reading_form() 
        
        # 如果没有汉字，直接返回基础信息
        if not re.search(r'[\u4e00-\u9faf]', surface):
            results.append(TokenData(
                surface=surface,
                reading=surface, # 非汉字原本就是读音（或者标点）
                okurigana=surface
            ))
            continue

        # 片假名 -> 平假名
        reading_hira = jaconv.kata2hira(reading_kata)

        # --- 智能剥离送假名逻辑 ---
        s_idx = len(surface)
        r_idx = len(reading_hira)
        suffix = ""
        
        # 从尾部倒序匹配
        while s_idx > 0 and r_idx > 0:
            s_char = surface[s_idx-1]
            r_char = reading_hira[r_idx-1]
            if s_char == r_char:
                suffix = s_char + suffix
                s_idx -= 1
                r_idx -= 1
            else:
                break
        
        kanji_part = surface[:s_idx]
        reading_part = reading_hira[:r_idx]

        # 构造数据对象
        token_data = TokenData(
            surface=surface,
            reading=reading_hira,
            kanji_base=kanji_part if kanji_part else surface,
            furigana=reading_part if kanji_part else reading_hira,
            okurigana=suffix
        )
        results.append(token_data)

    return results


# --- 4. 接口定义 ---

# 新接口：返回 JSON 数据
@app.post("/analyze", response_model=AnalysisResponse)
async def api_analyze(req: FuriganaRequest):
    if not req.text:
        return {"results": []}
    try:
        data = analyze_text_logic(req.text)
        return {"results": data}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")

# 旧接口：为了兼容，调用上面的逻辑并拼接 HTML
@app.post("/furigana")
async def api_furigana(req: FuriganaRequest):
    if not req.text:
        return {"html": ""}
    try:
        tokens = analyze_text_logic(req.text)
        html_output = ""
        
        for t in tokens:
            # 如果有 kanji_base 且它和 surface 不一样（或者有注音），说明需要生成 ruby
            if t.kanji_base and t.furigana:
                 # 格式: <ruby>食<rt>た</rt></ruby>べ
                 html_output += f"<ruby>{t.kanji_base}<rt>{t.furigana}</rt></ruby>{t.okurigana}"
            else:
                 # 纯假名或标点
                 html_output += t.surface
                 
        return {"html": html_output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)