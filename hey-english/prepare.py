#!/usr/bin/env python3
import gzip
import hashlib
import html as html_lib
import io
import json
import os
import re
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_HTML = ROOT / "source.html"
OUT_HTML = ROOT / "app" / "src" / "main" / "assets" / "index.html"
AUDIT = ROOT / "dictionary_audit.json"
TARGET_WORDS = 7500

TOP_URL = "https://raw.githubusercontent.com/shamilfrontend/english-russian-dictionary/main/top/top10000.json"
WIKDICT_URL = "https://download.wikdict.com/dictionaries/stardict/wikdict-en-ru.zip"
BACKUP_URL = "https://raw.githubusercontent.com/iuzhakov/English-Russian-vocabulary/master/words.json"

AMERICAN = {
    "colour":"color","colours":"colors","favourite":"favorite","favourites":"favorites",
    "centre":"center","centres":"centers","theatre":"theater","theatres":"theaters",
    "travelling":"traveling","travelled":"traveled","traveller":"traveler","travellers":"travelers",
    "cancelled":"canceled","cancelling":"canceling","labelled":"labeled","labelling":"labeling",
    "jewellery":"jewelry","grey":"gray","cheque":"check","programme":"program",
    "catalogue":"catalog","dialogue":"dialog","licence":"license","defence":"defense",
    "offence":"offense","practise":"practice","analyse":"analyze","organise":"organize",
    "organised":"organized","organising":"organizing","realise":"realize","realised":"realized",
    "recognise":"recognize","behaviour":"behavior","neighbour":"neighbor","neighbours":"neighbors",
    "honour":"honor","humour":"humor","labour":"labor","rumour":"rumor","flavour":"flavor",
    "fibre":"fiber","litre":"liter","metre":"meter","manoeuvre":"maneuver","pyjamas":"pajamas",
    "aeroplane":"airplane","tyre":"tire","kerb":"curb"
}

# Main everyday meanings for ambiguous high-frequency terms and explicit American-English choices.
OVERRIDES = {
    "are":"есть; являются","was":"был; была; было","were":"были; был; была",
    "will":"будет; вспомогательный глагол будущего времени","would":"бы; вспомогательный модальный глагол",
    "can":"мочь; уметь","could":"мог; мог бы","has":"имеет","had":"имел; имела; имели",
    "been":"был; была; было; форма глагола be","does":"делает; вспомогательный глагол",
    "did":"делал; сделал; вспомогательный глагол","made":"сделал; сделанный",
    "found":"нашёл; найденный","got":"получил; получилcя","given":"данный; учитывая",
    "used":"использованный; подержанный; привыкший","current":"текущий; нынешний; ток",
    "content":"содержание; контент; довольный","subject":"тема; предмет; субъект",
    "issue":"вопрос; проблема; выпуск","issues":"вопросы; проблемы; выпуски",
    "server":"сервер; официант; обслуживающий","user":"пользователь",
    "users":"пользователи","site":"сайт; место","web":"веб; интернет; паутина",
    "view":"вид; мнение; просматривать","contact":"контакт; связываться",
    "news":"новости","list":"список","product":"продукт; товар","products":"продукты; товары",
    "public":"общественный; публичный","privacy":"конфиденциальность; частная жизнь",
    "service":"услуга; сервис; обслуживание","services":"услуги; сервисы",
    "store":"магазин; хранить; запас","office":"офис; учреждение","level":"уровень",
    "love":"любовь; любить","team":"команда","box":"коробка; ящик","market":"рынок",
    "industry":"промышленность; отрасль","application":"приложение; заявление; применение",
    "applications":"приложения; заявления; применение","performance":"производительность; выступление",
    "social":"социальный; общественный","options":"варианты; параметры","rates":"тарифы; ставки",
    "building":"здание; строительство","result":"результат","major":"главный; основной; специальность",
    "space":"пространство; место; космос","hand":"рука; передавать","friend":"друг",
    "review":"обзор; отзыв; повторение","china":"Китай; фарфор","record":"запись; рекорд",
    "records":"записи; рекорды","mobile":"мобильный; подвижный","wireless":"беспроводной",
    "license":"лицензия; лицензировать","submit":"отправлять; представлять; подчиняться",
    "quote":"цитата; цитировать","picture":"изображение; картина; фотография",
    "pictures":"изображения; картины","photo":"фотография","children":"дети","shop":"магазин; делать покупки",
    "resources":"ресурсы","resource":"ресурс","people":"люди; народ","go":"идти; ехать",
    "time":"время; раз","right":"правильный; правый; право","well":"хорошо; колодец",
    "date":"дата; свидание; финик","back":"спина; назад; задний","post":"почта; пост; публиковать",
    "line":"линия; строка; очередь","power":"сила; мощность; власть","room":"комната; место",
    "credit":"кредит; доверие","men":"мужчины","left":"левый; ушёл; оставил","note":"заметка; записка; отмечать",
    "start":"начинать; начало","features":"особенности; функции","friend":"друг","server":"сервер; обслуживающий",
    "staff":"персонал; штат","article":"статья; предмет","articles":"статьи; предметы",
    "working":"работающий; работа","status":"статус; состояние","range":"диапазон; ряд",
    "court":"суд; корт; двор","files":"файлы","event":"событие","release":"выпуск; освобождать",
    "request":"запрос; просьба","making":"создание; изготовление","future":"будущее; будущий",
    "interest":"интерес; проценты; интересовать","reference":"ссылка; справка; рекомендация",
    "term":"термин; срок; семестр","journal":"журнал; дневник","notice":"уведомление; замечать",
    "track":"трек; путь; след; отслеживать","discussion":"обсуждение","log":"журнал; бревно",
    "trade":"торговля; ремесло; торговать","updated":"обновлённый","living":"жизнь; проживание; живущий",
    "display":"дисплей; отображать; показывать","director":"директор; режиссёр","past":"прошлое; прошлый; мимо",
    "land":"земля; приземляться","sound":"звук; звучать; исправный","present":"настоящий; подарок; представлять",
    "mark":"отметка; оценка; помечать","figure":"цифра; фигура; выяснять","entry":"вход; запись",
    "drug":"лекарство; наркотик","force":"сила; заставлять","employment":"занятость; работа",
    "commission":"комиссия; комиссионные","engine":"двигатель","board":"доска; совет; садиться на транспорт",
    "tips":"советы; чаевые; кончики","player":"игрок; проигрыватель","point":"точка; пункт; указывать",
    "points":"точки; пункты","address":"адрес; обращаться","community":"сообщество",
    "account":"аккаунт; счёт; учётная запись","program":"программа","programs":"программы",
    "college":"колледж; вуз","resume":"резюме; возобновлять","schedule":"расписание; планировать",
    "football":"американский футбол","soccer":"футбол","chips":"чипсы","fries":"картофель фри",
    "biscuit":"американская несладкая булочка; печенье","pants":"брюки; штаны",
    "subway":"метро","gas":"бензин; газ","gasoline":"бензин","bathroom":"ванная комната; туалет",
    "restroom":"туалет","zip code":"почтовый индекс","vacation":"отпуск; каникулы",
    "drugstore":"аптека; магазин товаров первой необходимости","pharmacy":"аптека","faucet":"кран",
    "elevator":"лифт","apartment":"квартира","closet":"встроенный шкаф; гардероб",
    "sidewalk":"тротуар","crosswalk":"пешеходный переход","truck":"грузовик",
    "sweater":"свитер","shorts":"шорты","nurse":"медсестра; медбрат","vest":"жилет",
    "pavement":"дорожное покрытие; мостовая","lorry":"грузовик","underground":"метро; подземный",
    "fall":"падать; осень","cookie":"печенье","candy":"конфеты","soda":"газировка",
    "eggplant":"баклажан","zucchini":"кабачок","cilantro":"кинза","arugula":"руккола",
    "diaper":"подгузник","pacifier":"соска-пустышка","stroller":"детская коляска",
    "sneakers":"кроссовки","sweatpants":"спортивные штаны","sweatshirt":"толстовка",
    "hoodie":"худи","underwear":"нижнее бельё","wallet":"кошелёк","backpack":"рюкзак",
    "carry-on":"ручная кладь","round-trip":"туда и обратно","one-way":"в одну сторону",
    "layover":"пересадка","boarding pass":"посадочный талон","gate":"выход на посадку",
    "aisle":"проход","seat belt":"ремень безопасности","downtown":"центр города",
    "uptown":"верхняя часть города","rideshare":"поездка через сервис такси","coworker":"коллега",
    "paycheck":"зарплата; расчётный чек","deadline":"крайний срок","feedback":"обратная связь",
    "follow-up":"последующее сообщение; продолжение","sign-up":"регистрация","login":"вход; логин",
    "username":"имя пользователя","password":"пароль","website":"веб-сайт","download":"скачивать; загрузка",
    "upload":"загружать; загрузка","screenshot":"снимок экрана","livestream":"прямая трансляция",
    "voicemail":"голосовая почта","text message":"текстовое сообщение","group chat":"групповой чат",
    "hangout":"неформальная встреча","hang out":"проводить время вместе","pick up":"забрать; подобрать",
    "drop off":"подвезти; оставить","figure out":"разобраться","find out":"выяснить",
    "show up":"появиться; прийти","work out":"тренироваться; получиться","run out":"закончиться",
    "fill out":"заполнить","check out":"посмотреть; выписаться","check in":"зарегистрироваться",
    "call back":"перезвонить","text back":"ответить сообщением","come over":"зайти в гости",
    "go ahead":"продолжай; начинай","hold on":"подожди","make sure":"убедиться",
    "no problem":"без проблем","sounds good":"звучит хорошо","my bad":"моя ошибка",
    "you're welcome":"пожалуйста","excuse me":"извините","i'm sorry":"мне жаль; извините",
    "of course":"конечно","right away":"сразу","a little bit":"немного",
    "pretty much":"почти; в основном","kind of":"вроде; немного","for sure":"точно; конечно",
    "actually":"на самом деле","basically":"в основном","seriously":"серьёзно",
    "awesome":"классный; отличный","cool":"классный; прохладный; хорошо","okay":"хорошо; нормально",
    "yep":"ага","nope":"нет; не-а","gonna":"разговорное going to","wanna":"разговорное want to",
    "gotta":"разговорное got to / have to"
}

BANNED = {
    "jan","feb","mar","apr","jun","jul","aug","sep","sept","oct","nov","dec",
    "gmt","pst","est","cst","mst","llc","inc","ltd","www","http","https","html","xhtml",
    "jpeg","jpg","png","gif","php","asp","rss","xml","dvd","dvds","cd","pdf","kb","mb","gb",
    "mph","km","cm","mm","ft","oz","lbs","isbn","issn","utc","api","sdk","cpu","gpu","ram",
    "ny","dc","la","ca","tx","fl","pa","az","wi","nc","sc","ct","mi","oh","va","ma","ga",
    "st","rd","ave","vs","etc","misc","faq","bbs","xxx"
}

def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent":"HEY-English-offline-builder/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

def normalize_word(value):
    s = str(value or "").strip().lower().replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    return AMERICAN.get(s, s)

def valid_word(word):
    if not word or word in BANNED:
        return False
    if len(word) > 36:
        return False
    if len(word) < 3:
        return False
    if not re.fullmatch(r"[a-z][a-z'.-]*(?: [a-z][a-z'.-]*){0,3}", word):
        return False
    letters = re.sub(r"[^a-z]", "", word)
    if len(letters) >= 3 and not re.search(r"[aeiouy]", letters):
        return False
    if any(len(part) == 1 and part not in {"a","i"} for part in word.split()):
        return False
    return True

def parse_stardict(zip_bytes):
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = z.namelist()
    idx_name = next(n for n in names if n.endswith(".idx"))
    ifo_name = next(n for n in names if n.endswith(".ifo"))
    dict_name = next((n for n in names if n.endswith(".dict")), None)
    dict_dz_name = next((n for n in names if n.endswith(".dict.dz")), None)
    info = z.read(ifo_name).decode("utf-8", "replace")
    offset_bits = 64 if re.search(r"^idxoffsetbits=64$", info, re.M) else 32
    seq_m = re.search(r"^sametypesequence=(.+)$", info, re.M)
    sequence = seq_m.group(1).strip() if seq_m else ""
    if dict_name:
        dict_data = z.read(dict_name)
    elif dict_dz_name:
        dict_data = gzip.decompress(z.read(dict_dz_name))
    else:
        raise RuntimeError("StarDict archive has no .dict or .dict.dz")
    idx = z.read(idx_name)
    pos = 0
    entries = {}
    while pos < len(idx):
        end = idx.find(b"\0", pos)
        if end < 0:
            break
        word = idx[pos:end].decode("utf-8", "replace")
        pos = end + 1
        if offset_bits == 64:
            if pos + 12 > len(idx): break
            off = struct.unpack(">Q", idx[pos:pos+8])[0]
            size = struct.unpack(">I", idx[pos+8:pos+12])[0]
            pos += 12
        else:
            if pos + 8 > len(idx): break
            off, size = struct.unpack(">II", idx[pos:pos+8])
            pos += 8
        raw = dict_data[off:off+size]
        if sequence:
            text = raw.decode("utf-8", "replace")
        else:
            # WikDict packages normally declare sametypesequence. Fallback keeps printable UTF-8 payload.
            text = raw.decode("utf-8", "replace")
        key = normalize_word(word)
        if key and key not in entries:
            entries[key] = text
    return entries

def clean_wikdict_definition(raw):
    if not raw:
        return ""
    t = html_lib.unescape(raw)
    t = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", " ; ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = t.replace("\x00", " ")
    t = re.sub(r"\s+", " ", t).strip()
    # Remove common language/POS labels but keep Russian lexical content.
    t = re.sub(r"(?i)\b(?:Russian|English|translation|translations|noun|verb|adjective|adverb|pronoun|preposition|conjunction|interjection|proper noun)\b\s*:?", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ;,.-")
    chunks = re.split(r"\s*[;|•]\s*|\s{2,}", t)
    out = []
    for c in chunks:
        c = c.strip(" ,;:-")
        if not c or not re.search(r"[А-Яа-яЁё]", c):
            continue
        c = re.sub(r"\[[^\]]*\]", "", c)
        c = re.sub(r"\([^)]*[A-Za-z][^)]*\)", "", c)
        c = re.sub(r"\s+", " ", c).strip(" ,;:-")
        if not c or len(c) > 100:
            continue
        if c not in out:
            out.append(c)
        if len(out) >= 4:
            break
    result = "; ".join(out)
    result = re.sub(r"\s+", " ", result).strip(" ;,")
    if len(result) > 150:
        result = result[:150].rsplit(" ",1)[0].rstrip(" ,;") + "…"
    return result

def clean_backup_translation(value):
    t = str(value or "").strip()
    t = re.sub(r"\(\(!?NEW!?\)\)|\(!?NEW!?\)|\(TR!\)", " ", t, flags=re.I)
    t = re.sub(r"\([^)]*[A-Za-z][^)]*\)", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,;")
    if not re.search(r"[А-Яа-яЁё]", t):
        return ""
    if re.search(r"[{}|=#<>]|&#|\b(?:XXX|ХХХ)\b", t, re.I):
        return ""
    if re.search(r"[A-Za-z]{2,}", t):
        return ""
    if len(t) > 120:
        t = t[:120].rsplit(" ",1)[0].rstrip(" ,;") + "…"
    return t

def translation_ok(t):
    if not t or len(t) < 2 or len(t) > 160:
        return False
    if not re.search(r"[А-Яа-яЁё]", t):
        return False
    if re.search(r"[{}|=#<>]|&#", t):
        return False
    if re.search(r"\b(?:XXX|ХХХ|перевод=|транскрипц)\b", t, re.I):
        return False
    return True

def patch_html(source, full_words):
    compact = json.dumps(full_words, ensure_ascii=False, separators=(",",":"))
    source, n = re.subn(
        r"const BASE_WORDS=\[.*?\];\nconst LEVELS",
        "const BASE_WORDS=" + compact + ";\nconst LEVELS",
        source,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise RuntimeError("Could not replace BASE_WORDS")
    # Completely remove first-run online dictionary download and cache.
    start = source.find('const EXTENDED_URL=')
    end = source.find('const ALPHABET=', start)
    if start < 0 or end < 0:
        raise RuntimeError("Could not locate online dictionary loader block")
    replacement = '''async function loadExtendedWords(){
 const note=document.getElementById("loadNote");
 if(note){note.textContent="Готово: 7 500 слов и выражений встроены в приложение и доступны полностью офлайн.";setTimeout(()=>note.style.display="none",2200)}
 cleanRemovedWordReferences();renderLevelCards();if(activeLevel)renderWords();if(currentFolderId)renderFolderView();updateProgress();updateGameCounts();
}
'''
    source = source[:start] + replacement + source[end:]
    # Prefer the native, local-only Android TTS bridge when running as APK.
    needle = 'function speak(text){\n'
    bridge = '''function speak(text){
 if(window.AndroidTTS&&typeof window.AndroidTTS.speak==="function"){
   try{if(window.AndroidTTS.speak(String(text||"")))return}catch(_){}
   toast("Нужен установленный офлайн-голос English (United States)");
   return;
 }
'''
    if needle not in source:
        raise RuntimeError("Could not locate speak()")
    source = source.replace(needle, bridge, 1)
    # Make state persistence even more defensive.
    persist_hook = '''window.addEventListener("pagehide",flushPersistentState);'''
    if persist_hook in source and 'window.addEventListener("freeze"' not in source:
        source = source.replace(persist_hook, 'window.addEventListener("freeze",flushPersistentState);\n' + persist_hook, 1)
    return source

def main():
    source = SOURCE_HTML.read_text(encoding="utf-8")
    m = re.search(r"const BASE_WORDS=(\[.*?\]);\nconst LEVELS", source, re.S)
    if not m:
        raise RuntimeError("BASE_WORDS not found")
    base = json.loads(m.group(1))
    if len(base) != 1000:
        raise RuntimeError("Expected 1000 curated base words, got %d" % len(base))
    # Normalize the single explanatory AmE marker in base so audit stays Cyrillic-only.
    for item in base:
        if item.get("en") == "fall":
            item["ru"] = "падать; осень"
    base_seen = {normalize_word(x["en"]) for x in base}

    print("Downloading frequency list...")
    top = json.loads(fetch_bytes(TOP_URL).decode("utf-8"))
    print("Downloading WikDict English-Russian...")
    wik_raw = parse_stardict(fetch_bytes(WIKDICT_URL))
    wik = {k: clean_wikdict_definition(v) for k,v in wik_raw.items()}
    print("WikDict entries:", len(wik_raw), "clean:", sum(1 for v in wik.values() if v))
    print("Downloading backup learner vocabulary...")
    backup_rows = json.loads(fetch_bytes(BACKUP_URL).decode("utf-8"))
    backup = {}
    for row in backup_rows:
        w = normalize_word(row.get("en"))
        if w and w not in backup:
            c = clean_backup_translation(row.get("ru"))
            if c:
                backup[w] = c

    selected = []
    seen = set(base_seen)
    source_counts = {"override":0,"wikdict":0,"backup":0}

    def add(word, preferred=None):
        w = normalize_word(word)
        if w in seen or not valid_word(w):
            return False
        ru = OVERRIDES.get(w, "")
        src = "override"
        if not ru:
            ru = wik.get(w, "")
            src = "wikdict"
        if not translation_ok(ru):
            ru = backup.get(w, "")
            src = "backup"
        if not translation_ok(ru):
            return False
        if re.search(r"[A-Za-z]{3,}", ru):
            # Only explicit conversational notes are allowed to contain Latin text.
            if w not in {"gonna","wanna","gotta"}:
                return False
        selected.append({"en":w,"ru":ru,"cat":"US словарь"})
        seen.add(w)
        source_counts[src] += 1
        return True

    # Use the original top-10k only as an ordering signal, never as a translation source.
    for row in top:
        add(row.get("word"))
        if len(base) + len(selected) >= TARGET_WORDS:
            break

    # Add useful American phrases before less frequent fallback words.
    if len(base) + len(selected) < TARGET_WORDS:
        for w in OVERRIDES:
            add(w)
            if len(base) + len(selected) >= TARGET_WORDS:
                break

    # Fill remaining slots from learner vocabulary order, but translations still prefer WikDict.
    if len(base) + len(selected) < TARGET_WORDS:
        for row in backup_rows:
            add(row.get("en"))
            if len(base) + len(selected) >= TARGET_WORDS:
                break

    # Last fallback: WikDict alphabetic entries, still heavily filtered.
    if len(base) + len(selected) < TARGET_WORDS:
        for w in sorted(wik):
            add(w)
            if len(base) + len(selected) >= TARGET_WORDS:
                break

    full = base + selected[:TARGET_WORDS-len(base)]
    if len(full) != TARGET_WORDS:
        raise RuntimeError("Only %d clean unique entries available" % len(full))

    # Final audits.
    keys = [normalize_word(x["en"]) for x in full]
    if len(set(keys)) != TARGET_WORDS:
        raise RuntimeError("Duplicate English entries remain")
    bad = []
    for i, item in enumerate(full, 1):
        en = str(item.get("en",""))
        ru = str(item.get("ru",""))
        flags = []
        if not en.strip(): flags.append("empty_en")
        if not translation_ok(ru): flags.append("bad_ru")
        if re.search(r"[{}|=#<>]|&#", ru): flags.append("markup")
        if re.search(r"\b(?:XXX|ХХХ|перевод=)\b", ru, re.I): flags.append("garbage")
        if flags:
            bad.append({"index":i,"en":en,"ru":ru,"flags":flags})
    if bad:
        raise RuntimeError("Final dictionary audit failed: %s" % bad[:5])

    final_html = patch_html(source, full)
    # Absolute runtime-offline guarantees for the web layer.
    forbidden = []
    if re.search(r"\bfetch\s*\(", final_html):
        forbidden.append("fetch")
    if re.search(r"https?://", final_html):
        forbidden.append("http_url")
    if "EXTENDED_URL" in final_html or "CACHE_KEY" in final_html:
        forbidden.append("online_dictionary_symbols")
    if forbidden:
        raise RuntimeError("Final HTML still contains network dependency: " + ", ".join(forbidden))

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(final_html, encoding="utf-8")
    digest = hashlib.sha256(final_html.encode("utf-8")).hexdigest()
    audit = {
        "total_words": len(full),
        "base_words": len(base),
        "added_words": len(full)-len(base),
        "unique_words": len(set(keys)),
        "source_counts": source_counts,
        "network_fetch_calls": len(re.findall(r"\bfetch\s*\(", final_html)),
        "http_urls": len(re.findall(r"https?://", final_html)),
        "runtime_dictionary_download": False,
        "storage": {
            "learned_words":"localStorage:hey_learned",
            "notebook":"localStorage:hey_notebook_folders_v3",
            "app_state":"localStorage:hey_app_state_v4"
        },
        "sha256_index_html": digest,
        "first_added": selected[:20],
        "last_words": full[-20:]
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
