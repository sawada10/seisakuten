
import numpy as np
# import MeCab
from wordcloud import WordCloud
import matplotlib.pyplot as plt

#関数の設定
def mecab_tokenizer(path):
    token_list = []
    # replaced_text = unicodedata.normalize("NFKC",text)
    # replaced_text = replaced_text.upper()
    # # replaced_text = re.sub(r'[【】 () （） 『』　「」]', '' ,replaced_text) #【】 () 「」　『』の除去
    # # replaced_text = re.sub(r'[\[\［］\]]', ' ', replaced_text)   # ［］の除去
    # # replaced_text = re.sub(r'[@＠]\w+', '', replaced_text)  # メンションの除去
    # # replaced_text = re.sub(r'\d+\.*\d*', '', replaced_text) #数字を0にする

    # parsed_lines = mecab.parse(replaced_text).split("\n")[:-2]

    # #表層系を取得
    # surfaces = [l.split("\t")[0] for l in parsed_lines]
    # #品詞を取得
    # pos = [l.split("\t")[1].split(",")[0] for l in parsed_lines]
    # #名詞、動詞、形容詞に絞り込み
    # target_pos = ["名詞", "動詞", "形容詞"]
    # token_list = [t for t , p in zip(surfaces, pos) if p in target_pos]
    with open(path) as f:
        lines = f.readlines()
        for l in lines:
            token_list.append(l.rstrip("\n"))
    
    #各トークンを少しスペースを空けて（' '）結合
    return ' '.join(token_list)

font_path="/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
#関数の実行
words = mecab_tokenizer("data/test0714.txt")

#色の設定
colormap="Paired"

wordcloud = WordCloud(
    background_color="white",
    width=800,
    height=800,
    font_path=font_path,
    colormap = colormap,
    stopwords=["する", "ある", "こと", "ない"],
    max_words=100,
    ).generate(words)

plt.figure(figsize=(10, 10))
plt.imshow(wordcloud, interpolation="bilinear")
plt.axis("off")
plt.show()
