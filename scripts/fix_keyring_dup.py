"""
Удаляет дублирующиеся ключи в секции [MOEXPy] файла keyring_pass.cfg.
Оставляет первый экземпляр ключа, удаляет последующие (вместе со строками значения,
которые идут с отступом).

Перед записью делает свой бэкап.
После записи проверяет: configparser парсит без DuplicateOptionError.
"""
import configparser, os, shutil, datetime as dt, re, sys

CFG = os.path.expanduser("~/.local/share/python_keyring/keyring_pass.cfg")
SECTION = "MOEXPy"

def backup(path: str) -> str:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{path}.predupfix_{ts}"
    shutil.copy2(path, bak)
    return bak

def fix_file(path: str) -> tuple[int, list[str]]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_section = False
    seen = set()          # ключи, уже встреченные в SECTION
    removed_keys = []     # какие ключи удалили (для отчёта)
    out_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # вход/выход из секции
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = (stripped == f"[{SECTION}]")
            out_lines.append(line)
            i += 1
            continue

        # пустые строки и комментарии — оставляем как есть
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            out_lines.append(line)
            i += 1
            continue

        # ключ = значение  (без ведущих пробелов, либо с ними — но ключ только без отступа)
        m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*(.*)$", line)
        if in_section and m:
            key = m.group(1)
            if key in seen:
                # дубликат: пропускаем эту строку + все последующие строки значения
                # (значение может быть многострочным: строки с отступом / пустые внутри)
                removed_keys.append(key)
                i += 1
                # пропускаем строки продолжения значения: с отступом (таб/пробел)
                while i < len(lines) and lines[i][:1] in (" ", "\t") and lines[i].strip() != "":
                    i += 1
                continue
            else:
                seen.add(key)
                out_lines.append(line)
                i += 1
                continue

        # всё остальное (включая строки значения) — как есть
        out_lines.append(line)
        i += 1

    # пишем только если есть что удалять
    if removed_keys:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)

    return len(removed_keys), removed_keys

def validate(path: str) -> str:
    p = configparser.ConfigParser()
    try:
        p.read(path)
        return "OK"
    except Exception as e:
        return f"FAIL: {type(e).__name__}: {e}"

def main():
    print("CFG:", CFG)
    if not os.path.exists(CFG):
        print("НЕТ ФАЙЛА"); sys.exit(2)

    bak = backup(CFG)
    print("Бэкап:", bak)

    n, removed = fix_file(CFG)
    print(f"Удалено дублирующихся ключей: {n}")
    if removed:
        print("Ключи:", ", ".join(removed))

    print("Валидация:", validate(CFG))

    # дополнительные проверки
    with open(CFG, "r", encoding="utf-8") as f:
        content = f.read()
    print("grep token0 (^token0):", len(re.findall(r"^token0", content, flags=re.M)))
    print("grep 'nl -ba':", "ЕСТЬ" if "nl -ba" in content else "нет")

if __name__ == "__main__":
    main()
