import anthropic
import json
import os
import time

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

THEMES = [
    {"id": "comparison", "label": "人と比較してしまう"},
    {"id": "loneliness", "label": "孤独を感じる"},
    {"id": "people_pleasing", "label": "人に合わせすぎてしまう"},
    {"id": "unforgiving", "label": "誰かを許せない"},
    {"id": "jealousy", "label": "嫉妬してしまう"},
    {"id": "relationship_reset", "label": "人間関係をリセットしたくなる"},
    {"id": "cant_be_honest", "label": "本音が言えない"},
    {"id": "identity_lost", "label": "自分が何者かわからない"},
    {"id": "no_confidence", "label": "自信が持てない"},
    {"id": "no_purpose", "label": "やりたいことが見つからない"},
    {"id": "past_regret", "label": "過去を引きずってしまう"},
    {"id": "emotional_control", "label": "感情のコントロールができない"},
    {"id": "perfectionism", "label": "完璧主義で疲れてしまう"},
    {"id": "self_dislike", "label": "自分を好きになれない"},
    {"id": "work_meaningless", "label": "仕事の意味が見えない"},
    {"id": "career_change", "label": "転職すべきか迷っている"},
    {"id": "effort_unrewarded", "label": "努力が報われない気がする"},
    {"id": "work_purpose", "label": "何のために働くかわからない"},
    {"id": "dream_abandon", "label": "夢を諦めるべきか迷っている"},
    {"id": "life_meaning", "label": "生きる意味がわからない"},
    {"id": "fear_of_change", "label": "変化が怖い"},
    {"id": "happiness_unknown", "label": "幸せとは何かわからない"},
    {"id": "death_thoughts", "label": "死について考えてしまう"},
    {"id": "time_wasted", "label": "時間が無駄に過ぎている気がする"},
    {"id": "choice_regret", "label": "選択を後悔してしまう"},
    {"id": "world_dissatisfaction", "label": "世の中への不満"},
    {"id": "money_happiness", "label": "お金と幸せの関係"},
    {"id": "ai_era", "label": "AIの時代をどう生きるか"},
    {"id": "no_correct_answer", "label": "正解のない時代をどう生きるか"},
    {"id": "powerlessness", "label": "環境や社会への無力感"},
]

BATCH_SIZE = 3


def generate_batch(themes_batch):
    theme_descriptions = "\n".join(
        [f'- ID: {t["id"]}, テーマ: {t["label"]}' for t in themes_batch]
    )

    prompt = f"""以下のテーマそれぞれについて、哲学・文学・仏教・心理学・詩・日本の古典から10件の言葉を生成してください。
東洋（中国・インド・日本）・西洋（ギリシャ・ヨーロッパ・アメリカ）・日本をバランスよく含めること。

テーマ一覧：
{theme_descriptions}

各言葉のJSON形式：
{{
  "id": "テーマid_連番（例: comparison_1）",
  "theme_id": "テーマid",
  "text": "言葉本文（日本語で、原文の場合は日本語訳）",
  "author": "著者名（日本語）",
  "genre": "哲学/文学/仏教/心理学/詩/日本の古典 のいずれか一つ",
  "source": "出典（書籍名・作品名）",
  "year": "年代（例: 紀元前399年、1946年、17世紀など）",
  "explanation": "このテーマとの関係を100文字程度で説明"
}}

出力はJSON配列のみ。説明文や前置きは不要。必ず各テーマ10件ずつ、合計{len(themes_batch) * 10}件を出力すること。"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
    # Extract JSON array
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON array found in response: {text[:200]}")
    return json.loads(text[start:end])


def main():
    output_path = "/home/user/PDB/philosophy-database.json"

    # Load existing progress if any
    all_entries = []
    done_theme_ids = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        all_entries = existing.get("entries", [])
        done_theme_ids = {e["theme_id"] for e in all_entries}
        print(f"Resuming: {len(all_entries)} entries already done for themes: {done_theme_ids}")

    remaining = [t for t in THEMES if t["id"] not in done_theme_ids]

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i : i + BATCH_SIZE]
        batch_labels = [t["label"] for t in batch]
        print(f"Generating batch {i//BATCH_SIZE + 1}: {batch_labels}")

        try:
            entries = generate_batch(batch)
            all_entries.extend(entries)
            print(f"  -> Got {len(entries)} entries (total: {len(all_entries)})")
        except Exception as e:
            print(f"  ERROR: {e}")
            raise

        # Save progress after each batch
        db = {"themes": THEMES, "entries": all_entries}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

        if i + BATCH_SIZE < len(remaining):
            time.sleep(2)

    # Organize by theme
    db = {"themes": THEMES, "entries": all_entries}

    output_path = "/home/user/PDB/philosophy-database.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(all_entries)} entries to {output_path}")

    # Validate counts
    for theme in THEMES:
        count = sum(1 for e in all_entries if e.get("theme_id") == theme["id"])
        status = "OK" if count == 10 else f"WARN: {count} entries"
        print(f"  {theme['label']}: {status}")


if __name__ == "__main__":
    main()
