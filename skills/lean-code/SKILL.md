---
name: lean-code
description: 初期開発フェーズ向け。コード生成時に過剰なフォールバック・後方互換・重複を防止する。コードの生成・修正・リファクタリング時に使用する。
---

# Lean Code スキル

## いつ使うか

コードの生成・修正・リファクタリングを行うすべての場面で適用する。

## 生成前チェック（コードを書く前に必ず確認）

1. このコードに外部利用者はいるか？ → いなければフォールバック不要
2. 旧バージョンとの互換が必要な理由はあるか？ → なければ互換コード不要
3. この処理は既にコードベースのどこかに存在するか？ → あれば再利用する

## 禁止パターン

以下のパターンが出現したら、書く前に立ち止まって削除する。

```
# NG: 存在しない旧形式へのフォールバック
if hasattr(obj, 'new_method'):
    obj.new_method()
else:
    obj.old_method()  # old_method は存在しない

# NG: 念のための防御的デフォルト値
value = config.get('key', some_complex_fallback_logic())

# NG: 同じバリデーションが2箇所に存在
def create_user(name):
    if not name or len(name) > 100:  # ← validate_name() を使え
        raise ValueError()

# NG: 誰も使っていないオプション引数
def process(data, legacy_mode=False, compat_version=None):
    ...
```

## 推奨パターン

```
# OK: 直接的に書く
obj.new_method()

# OK: 設定がなければエラーにする（隠さない）
value = config['key']

# OK: バリデーションは1箇所
def validate_name(name):
    if not name or len(name) > 100:
        raise ValueError()

# OK: 今必要な引数だけ
def process(data):
    ...
```

## 生成後セルフレビュー

コードを出力する前に、以下を自問する。

- このコードに「もし〜だったら」で始まる防御的処理はあるか？ → その「もし」は今起こりうるか？
- 同じことを2回書いていないか？
- 削除しても今の機能に影響しないコードはあるか？ → あれば削除する
