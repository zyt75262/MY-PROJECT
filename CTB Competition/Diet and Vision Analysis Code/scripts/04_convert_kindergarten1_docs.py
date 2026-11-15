import win32com.client

from common import PROCESSED_DIR, RAW_DIR

doc_dir = RAW_DIR / "kindergarten1_recipes"
out_dir = PROCESSED_DIR / "kindergarten1_recipe_text"
out_dir.mkdir(parents=True, exist_ok=True)

docs = sorted(
    path for path in doc_dir.glob("*.doc")
    if not path.name.startswith("~$")
)
print("recipe documents:", len(docs))

word = win32com.client.Dispatch("Word.Application")
word.Visible = False
for index, path in enumerate(docs, start=1):
    doc = word.Documents.Open(str(path), ReadOnly=True)
    text = doc.Content.Text
    doc.Close(False)
    out_name = "recipe_%02d.txt" % index
    (out_dir / out_name).write_text(text, encoding="utf-8")
    print("converted", path.name, "->", out_name)
word.Quit()

print("done, text files in", out_dir.name)
