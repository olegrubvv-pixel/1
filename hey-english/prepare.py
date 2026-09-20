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
    if not t or len(t) > 160:
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



# Additional American-English normalization used by the strict learner dictionary.
AMERICAN.update({
    "coloured":"colored","colouring":"coloring","colourful":"colorful",
    "favour":"favor","favours":"favors","favoured":"favored",
    "honours":"honors","honoured":"honored",
    "flavours":"flavors","neighbourhood":"neighborhood","behaviours":"behaviors",
    "rumours":"rumors","harbour":"harbor","harbours":"harbors","armour":"armor",
    "centred":"centered","metres":"meters","litres":"liters","fibres":"fibers",
    "analysed":"analyzed","analysing":"analyzing","realising":"realizing",
    "recognised":"recognized","recognising":"recognizing",
    "apologise":"apologize","apologised":"apologized",
    "emphasise":"emphasize","emphasised":"emphasized",
    "summarise":"summarize","summarised":"summarized",
    "criticise":"criticize","criticised":"criticized",
    "modelling":"modeling","modelled":"modeled",
    "programmes":"programs","cheques":"checks","tyres":"tires",
    "aeroplanes":"airplanes","maths":"math","cosy":"cozy","ageing":"aging",
    "judgement":"judgment","fulfil":"fulfill","fulfilment":"fulfillment",
    "enrol":"enroll","enrolment":"enrollment","aluminium":"aluminum",
    "gaol":"jail","mould":"mold","plough":"plow"
})
BRITISH_ONLY={"petrol","lorry","postcode","mack"}
NAMES_URL = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/names.zip"
COMMON_NAME_WORDS={"will","bill","mark","rose","grace","hope","faith","joy","summer","may","april","june","august","hunter","mason","grant","frank","victor","robin","dawn","crystal","amber","pearl","violet","lily","olive","cherry","clay","dean","dale","lance","drew","chase","sky","river","brook","melody","harmony","charity","patience","angel","art","ray","gene","jean","cliff","forest","wood","stone","reed","lane","candy","ginger","holly","ivy","iris","jasmine","hazel","ruby","opal","autumn","winter"}

OVERRIDES.update({
    "the":"этот; тот; определённый артикль",
    "its":"его; её; свой (для неодушевлённого)",
    "than":"чем",
    "should":"следует; должен; стоило бы",
    "being":"бытие; являющийся; будучи",
    "going":"идущий; собирающийся",
    "since":"с тех пор как; поскольку; с",
    "media":"средства массовой информации; медиа",
    "led":"вёл; привёл; руководил",
    "ball":"мяч; шар; бал",
    "billion":"миллиард",
    "fifth":"пятый",
    "eighty":"восемьдесят",
    "ninety":"девяносто",
    "knocked":"постучал; стукнул; сбил",
    "rode":"ехал; ездил; ехал верхом",
    "strawberry":"клубника; земляника",
    "steer":"управлять; направлять; рулить",
    "tow":"буксировать; буксировка",
    "thrill":"острое волнение; волновать",
    "directive":"директива; указание",
    "disadvantage":"недостаток; невыгодное положение",
    "energetic":"энергичный",
    "funk":"фанк; уныние; страх",
    "badass":"разговорное: крутой; очень впечатляющий человек",
    "upward":"вверх; направленный вверх",
    "appoint":"назначать; определять на должность",
    "crisp":"хрустящий; свежий; чёткий",
    "delegate":"делегат; представитель; делегировать",
    "expelled":"исключённый; выдворенный",
    "flora":"флора; растительный мир",
    "idle":"бездействующий; праздный; неработающий",
    "jumper":"прыгун; сарафан без рукавов",
    "hulk":"громила; огромная развалина",
    "slick":"гладкий; скользкий; ловкий",
    "virgin":"девственник; девственница; девственный",
    "grace":"грация; изящество; благодать",
    "miller":"мельник",
    "smith":"кузнец",
    "jean":"джинсовая ткань; джинсовый",
    "fuck":"грубое: трахаться; испортить; чёрт",
    "fucked":"грубое: испорченный; в тяжёлой ситуации",
    "bullshit":"грубое: чушь; ерунда; враньё",
    "dick":"грубое: пенис; неприятный человек",
    "penis":"пенис; мужской половой орган",
    "vagina":"влагалище; женский половой орган",
    "shitty":"грубое: паршивый; ужасный",
    "goddamn":"ругательное: проклятый; чёртов",
    "cunt":"крайне грубое: женские гениталии; оскорбление"
})


OVERRIDES.update({
    "commute":"ездить на работу или учёбу; поездка на работу или учёбу",
    "calculator":"калькулятор",
    "culinary":"кулинарный",
    "bun":"булочка; пучок волос",
    "batter":"жидкое тесто; сильно бить",
    "aha":"ага; вот оно что",
    "antarctic":"антарктический",
    "asteroid":"астероид",
    "bedtime":"время ложиться спать",
    "belongings":"личные вещи; имущество",
    "blush":"румянец; краснеть",
    "captivity":"плен; неволя",
    "catastrophe":"катастрофа; бедствие",
    "chemotherapy":"химиотерапия",
    "concussion":"сотрясение мозга",
    "consulate":"консульство",
    "contend":"бороться; соперничать; утверждать",
    "convict":"осуждённый; заключённый; признавать виновным",
    "craving":"сильная тяга; страстное желание",
    "din":"грохот; гул; сильный шум",
    "windy":"ветреный",
    "abruptly":"резко; внезапно",
    "aquarium":"аквариум"
})

# ---------- Strict v2 dictionary validation ----------
STRICT_REJECT = {
    "advertisement","advertisements","homepage","webpage","webpages","webmaster",
    "javascript","stylesheet","checkbox","dropdown","toolbar","webcam","webcast",
    "shareware","freeware","firmware","middleware","localhost",
}

def strict_word(raw):
    original = str(raw or "").strip()
    if not original:
        return ""
    if original[:1].isupper() and original.lower() not in {"i"}:
        return ""
    if original.isupper():
        return ""
    w = normalize_word(original)
    if w in BANNED or w in STRICT_REJECT or w in BRITISH_ONLY:
        return ""
    if len(w) < 3 or len(w) > 24:
        return ""
    if not re.fullmatch(r"[a-z]+(?:-[a-z]+)?", w):
        return ""
    if "--" in w or w.startswith("-") or w.endswith("-"):
        return ""
    letters = w.replace("-", "")
    if not re.search(r"[aeiouy]", letters):
        return ""
    return w

def strip_wiki_markup(value):
    t = html_lib.unescape(str(value or ""))
    t = t.replace("\x00", " ")
    t = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "; ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    for _ in range(4):
        prev=t
        t = re.sub(r"\[\[[^\[\]|]*\|([^\[\]]+)\]\]", r"\1", t)
        t = re.sub(r"\[\[([^\[\]]+)\]\]", r"\1", t)
        t = re.sub(r"\{\{[^{}]*\}\}", " ", t)
        if t==prev:
            break
    t = re.sub(r"\[(?:https?://|//)[^\]\s]+(?:\s+([^\]]+))?\]", lambda m: m.group(1) or " ", t)
    t = t.replace("'''"," ").replace("''"," ")
    t = re.sub(r"(?i)#(?:русский|russian|english)\b", " ", t)
    t = re.sub(r"(?i)\b(?:Russian|English|translation|translations|noun|verb|adjective|adverb|pronoun|preposition|conjunction|interjection|proper noun)\b\s*:?", " ", t)
    t = re.sub(r"[\r\n\t]+", "; ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" ;,:.-")

def strict_clean_translation(value):
    t = strip_wiki_markup(value)
    if not t:
        return ""
    t = re.sub(r"\([^)]*[A-Za-z][^)]*\)", " ", t)
    t = re.sub(r"\[[^\]]*\]", " ", t)
    t = re.sub(r"\{[^}]*\}", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ;,:.-")
    pieces = re.split(r"\s*[;|•]\s*|\s+/+\s*", t)
    clean=[]
    for p in pieces:
        p=re.sub(r"\s+"," ",p).strip(" ;,:.-")
        if not p or len(p)>90:
            continue
        if not re.search(r"[А-Яа-яЁё]",p):
            continue
        if re.search(r"[\[\]{}<>#=]|&#|https?://|www\.",p,re.I):
            continue
        if re.search(r"[A-Za-z]{2,}",p):
            continue
        if p.count("(")!=p.count(")") or p.count("[")!=p.count("]"):
            continue
        if re.search(r"[(\[,;:/-]\s*$",p):
            continue
        letters=re.findall(r"[A-Za-zА-Яа-яЁё]",p)
        if letters:
            cy=sum(bool(re.match(r"[А-Яа-яЁё]",x)) for x in letters)
            if cy/len(letters)<0.90:
                continue
        if p not in clean:
            clean.append(p)
        if len(clean)>=4:
            break
    out="; ".join(clean).strip(" ;,")
    if len(out)>150:
        out=out[:150].rsplit(" ",1)[0].rstrip(" ,;:.")+"…"
    return out

def ru_stems(t):
    stop={"это","или","как","для","при","что","кто","тот","эта","эти","его","ее","её","они","она","оно","быть","есть"}
    words=re.findall(r"[а-яё]{3,}",str(t or "").lower())
    return {w[:5] for w in words if w not in stop}

def strict_translation_ok(t):
    if not t or len(t)<1 or len(t)>160:
        return False
    if not re.search(r"[А-Яа-яЁё]",t):
        return False
    if re.search(r"[\[\]{}<>#=]|&#|https?://|www\.|_{2,}",t,re.I):
        return False
    if re.search(r"\b(?:XXX|ХХХ|перевод|транскрипц|undefined|null)\b",t,re.I):
        return False
    if re.search(r"[A-Za-z]{2,}",t):
        return False
    if re.search(r"\d",t):
        return False
    if re.search(r"(?i)(?:^|[^а-яё])(?:хуй|хуя|хуе|пизд|ебан|ёбан|ебат|ёбат|бляд|блять|заёб|говня|сраный)(?:[^а-яё]|$)",t):
        return False
    if t.count("(")!=t.count(")") or t.count("[")!=t.count("]"):
        return False
    if re.search(r"[(\[,;:/-]\s*$",t):
        return False
    return True


def proper_name_like_translation(t):
    pieces=[p.strip() for p in str(t or "").split(";") if p.strip()]
    if not pieces:
        return False
    flags=[]
    for p in pieces:
        first=re.search(r"[А-Яа-яЁё]",p)
        if not first:
            continue
        ch=first.group(0)
        flags.append(bool(re.match(r"[А-ЯЁ]",ch)))
    return bool(flags) and all(flags)

def pick_translation(word, top_raw, wik_raw, backup_raw):
    if word in OVERRIDES:
        v=OVERRIDES[word]
        special={
            "gonna":"разговорное: собираюсь; буду",
            "wanna":"разговорное: хотеть",
            "gotta":"разговорное: нужно; должен"
        }
        v=special.get(word,v)
        return v,"override","curated"

    vals=[]
    for src,raw in (("top",top_raw),("wikdict",wik_raw),("backup",backup_raw)):
        v=strict_clean_translation(raw)
        if strict_translation_ok(v):
            vals.append((src,v,ru_stems(v),proper_name_like_translation(v)))

    # If at least one source gives a normal lowercase lexical meaning, do not pick a
    # capitalized personal/place/brand-name reading from another source.
    normal=[x for x in vals if not x[3]]
    if normal:
        vals=normal
    elif vals:
        return "","","rejected"

    for i in range(len(vals)):
        for j in range(i+1,len(vals)):
            if vals[i][2] and vals[j][2] and vals[i][2].intersection(vals[j][2]):
                pair=[vals[i],vals[j]]
                pair.sort(key=lambda x:(0 if x[0]=="wikdict" else 1,len(x[1])))
                return pair[0][1],pair[0][0],"cross_source"

    for src,v,_,_ in vals:
        if src=="wikdict":
            return v,src,"single_source"
    for src,v,_,_ in vals:
        if src=="backup" and len(v)<=70:
            return v,src,"single_source"
    return "","","rejected"


def load_person_names():
    try:
        z=zipfile.ZipFile(io.BytesIO(fetch_bytes(NAMES_URL)))
        out=set()
        for n in z.namelist():
            if n.endswith("male.txt") or n.endswith("female.txt"):
                for line in z.read(n).decode("utf-8","replace").splitlines():
                    name=line.strip().lower()
                    if re.fullmatch(r"[a-z]+",name):
                        out.add(name)
        return out
    except Exception:
        # Explicit fallback catches names that previously slipped through.
        return {"irene","ned","john","david","james","michael","george","paul","peter","william","robert","thomas","louis","richard","joe","mary","charles","henry","martin","harry","steve","daniel","jim","ryan","adam","andrew","edward","joseph","stephen","howard","sarah","simon","elizabeth","jason","luke","jane","anthony","arthur","alexander","francis","gary","allen","matthew","patrick","walter","ann","bruce","ethan","frances"}

def main():
    source = SOURCE_HTML.read_text(encoding="utf-8")
    m = re.search(r"const BASE_WORDS=(\[.*?\]);\nconst LEVELS", source, re.S)
    if not m:
        raise RuntimeError("BASE_WORDS not found")
    base = json.loads(m.group(1))
    if len(base) != 1000:
        raise RuntimeError("Expected 1000 curated base words, got %d" % len(base))
    for item in base:
        if item.get("en") == "fall":
            item["ru"] = "падать; осень"
    base_seen={normalize_word(x["en"]) for x in base}
    if len(base_seen)!=len(base):
        raise RuntimeError("Duplicate word in curated 1000-word base")

    print("Downloading frequency list...")
    top=json.loads(fetch_bytes(TOP_URL).decode("utf-8"))
    print("Downloading WikDict English-Russian...")
    wik_raw=parse_stardict(fetch_bytes(WIKDICT_URL))
    print("Downloading independent backup vocabulary...")
    backup_rows=json.loads(fetch_bytes(BACKUP_URL).decode("utf-8"))
    backup={}
    for row in backup_rows:
        w=normalize_word(row.get("en"))
        if w and w not in backup:
            backup[w]=row.get("ru","")

    # Use a larger, independent frequency list so rejected/noisy entries are
    # replaced by the nearest normal-frequency word instead of relaxing validation.
    from wordfreq import top_n_list
    freq_words=top_n_list("en", 30000, ascii_only=True)
    top_map={}
    for row in top:
        tw=normalize_word(row.get("word",""))
        if tw and tw not in top_map:
            top_map[tw]=row.get("translation","")

    person_names=load_person_names()

    selected=[]
    seen=set(base_seen)
    source_counts={"override":0,"top":0,"wikdict":0,"backup":0}
    confidence_counts={"curated":0,"cross_source":0,"single_source":0}
    rejected={"invalid_word":0,"duplicate":0,"no_clean_translation":0}
    selected_ranks=[]

    for rank,raw_word in enumerate(freq_words,1):
        w=strict_word(raw_word)
        if not w:
            rejected["invalid_word"]+=1
            continue
        if w in seen:
            rejected["duplicate"]+=1
            continue
        if w in person_names and w not in COMMON_NAME_WORDS and w not in OVERRIDES:
            rejected["invalid_word"]+=1
            continue
        ru,src,conf=pick_translation(w,top_map.get(w,""),wik_raw.get(w,""),backup.get(w,""))
        if not strict_translation_ok(ru):
            rejected["no_clean_translation"]+=1
            continue
        idx=len(base)+len(selected)
        if idx<3000 and conf=="single_source":
            rejected["no_clean_translation"]+=1
            continue
        level="A1" if idx<1500 else "A2" if idx<3000 else "B1" if idx<5000 else "B2"
        selected.append({"en":w,"ru":ru,"cat":"US словарь"})
        selected_ranks.append({"word":w,"source_rank":rank,"output_rank":idx+1,"level":level,"translation_source":src,"confidence":conf})
        seen.add(w)
        source_counts[src]+=1
        confidence_counts[conf]+=1
        if len(base)+len(selected)>=TARGET_WORDS:
            break

    if len(base)+len(selected)<TARGET_WORDS:
        raise RuntimeError("Frequency source did not provide enough clean entries: %d/%d" % (len(base)+len(selected),TARGET_WORDS))

    full=base+selected[:TARGET_WORDS-len(base)]
    keys=[normalize_word(x["en"]) for x in full]
    if len(full)!=TARGET_WORDS or len(set(keys))!=TARGET_WORDS:
        raise RuntimeError("Final size/uniqueness check failed")

    expected={"A0":500,"A1":1000,"A2":1500,"B1":2000,"B2":2500}
    actual={"A0":0,"A1":0,"A2":0,"B1":0,"B2":0}
    for i in range(len(full)):
        lv="A0" if i<500 else "A1" if i<1500 else "A2" if i<3000 else "B1" if i<5000 else "B2"
        actual[lv]+=1
    if actual!=expected:
        raise RuntimeError("Level counts changed: %r" % actual)

    suspicious=[]
    for i,item in enumerate(full,1):
        en=str(item.get("en","")).strip()
        ru=str(item.get("ru","")).strip()
        flags=[]
        if not en: flags.append("empty_en")
        if i>1000 and not strict_word(en): flags.append("invalid_extended_word")
        if not strict_translation_ok(ru): flags.append("bad_translation")
        if re.search(r"[\[\]{}<>#=]|&#|https?://|www\.|_{2,}",ru,re.I): flags.append("markup")
        if re.search(r"[A-Za-z]{2,}",ru): flags.append("latin_leak")
        if ru.count("(")!=ru.count(")"): flags.append("broken_parentheses")
        if flags:
            suspicious.append({"index":i,"en":en,"ru":ru,"flags":flags})
    if suspicious:
        raise RuntimeError("Strict final audit failed: %s" % suspicious[:10])

    final_html=patch_html(source,full)
    forbidden=[]
    if re.search(r"\bfetch\s*\(",final_html): forbidden.append("fetch")
    if re.search(r"https?://",final_html): forbidden.append("http_url")
    if "EXTENDED_URL" in final_html or "CACHE_KEY" in final_html: forbidden.append("online_dictionary_symbols")
    if forbidden:
        raise RuntimeError("Final HTML still contains network dependency: "+", ".join(forbidden))

    OUT_HTML.parent.mkdir(parents=True,exist_ok=True)
    OUT_HTML.write_text(final_html,encoding="utf-8")
    digest=hashlib.sha256(final_html.encode("utf-8")).hexdigest()

    rank_gaps=[]
    prev=None
    for x in selected_ranks:
        if prev is not None:
            rank_gaps.append(x["source_rank"]-prev)
        prev=x["source_rank"]

    audit={
        "audit_version":"strict-v2",
        "total_words":len(full),
        "unique_words":len(set(keys)),
        "level_counts":actual,
        "extended_words":len(selected),
        "source_counts":source_counts,
        "confidence_counts":confidence_counts,
        "rejected_candidates":rejected,
        "selection_strategy":"wordfreq frequency-order; invalid/duplicate/noisy entries replaced by the next clean neighboring-frequency word while output level boundaries remain fixed",
        "last_selected_source_rank":selected_ranks[-1]["source_rank"],
        "max_neighbor_rank_gap":max(rank_gaps or [0]),
        "suspicious_after_final_audit":0,
        "network_fetch_calls":len(re.findall(r"\bfetch\s*\(",final_html)),
        "http_urls":len(re.findall(r"https?://",final_html)),
        "runtime_dictionary_download":False,
        "storage":{
            "learned_words":"localStorage:hey_learned",
            "notebook":"localStorage:hey_notebook_folders_v3",
            "app_state":"localStorage:hey_app_state_v4"
        },
        "sha256_index_html":digest,
        "sample_first_extended":selected_ranks[:25],
        "sample_last_extended":selected_ranks[-25:]
    }
    AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
