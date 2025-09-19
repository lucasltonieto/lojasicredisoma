import uuid
import re
from urllib.parse import unquote, quote
from flask import Flask, request, redirect, render_template, make_response, url_for
from vercel_wsgi import handle_request

app = Flask(__name__)

CATALOGO = {
    "89": {"nome": "Prato", "preco": 95.90},
    "50": {"nome": "Camiseta", "preco": 20.55},
}

STORE = {}

def _normalize_key(k: str) -> str:
    return k.lower().replace("+", "").replace(" ", "")

def _to_int(val, default=1):
    if val is None:
        return default
    try:
        return int(val)
    except Exception:
        m = re.search(r"-?\d+", str(val))
        if m:
            try:
                return int(m.group(0))
            except Exception:
                return default
        return default

def _add_item(cart: dict, nome: str, preco, qtd=1):
    if not nome:
        return
    try:
        preco = float(str(preco).replace(",", "."))
    except Exception:
        return
    try:
        qtd = int(qtd)
    except Exception:
        qtd = 1

    if nome in cart:
        cart[nome]["qtd"] += qtd
        cart[nome]["preco"] = preco
    else:
        cart[nome] = {"preco": preco, "qtd": qtd}

def _add_code(cart: dict, codigo: str, qtd=1):
    if not codigo:
        return
    codigo = unquote(str(codigo)).strip()
    qtd = _to_int(qtd, 1)
    item = CATALOGO.get(codigo)
    if not item:
        return
    _add_item(cart, item["nome"], item["preco"], qtd)

def _get_cid_from_request():
    cid_url = request.args.get("cid")
    cid_cookie = request.cookies.get("cid")
    return cid_url, cid_cookie

def _ensure_cid_and_cookie():
    cid_url, cid_cookie = _get_cid_from_request()
    if cid_url:
        resp = None
        if cid_cookie != cid_url:
            resp = make_response(None)
            resp.set_cookie("cid", cid_url, max_age=7 * 24 * 3600, samesite="Lax")
        return cid_url, resp
    if cid_cookie:
        resp = make_response(redirect(url_for("index", cid=cid_cookie)))
        resp.set_cookie("cid", cid_cookie, max_age=7 * 24 * 3600, samesite="Lax")
        return None, resp
    new_cid = uuid.uuid4().hex[:8]
    resp = make_response(redirect(url_for("index", cid=new_cid)))
    resp.set_cookie("cid", new_cid, max_age=7 * 24 * 3600, samesite="Lax")
    return None, resp

@app.route("/")
def index():
    cid, resp = _ensure_cid_and_cookie()
    if resp is not None:
        return resp

    cid = request.args.get("cid")
    cart = STORE.get(cid, {})
    changed = False
    qp = request.args

    if qp.get("clear"):
        cart = {}
        changed = True

    for key in qp.keys():
        if _normalize_key(key) in {"rm", "remove", "del"}:
            rm_val = qp.get(key)
            if rm_val:
                keyval = unquote(str(rm_val)).strip()
                if keyval in cart:
                    del cart[keyval]
                    changed = True
                else:
                    item = CATALOGO.get(keyval)
                    if item and item["nome"] in cart:
                        del cart[item["nome"]]
                        changed = True
            break

    codes_val = None
    for key in qp.keys():
        if _normalize_key(key) in {"codes", "itens", "items", "codigos"}:
            codes_val = qp.get(key)
            break
    if codes_val:
        for chunk in str(codes_val).split(";"):
            if not chunk.strip():
                continue
            parts = [p.strip() for p in chunk.split("|")]
            if len(parts) == 1:
                _add_code(cart, parts[0], 1)
            else:
                _add_code(cart, parts[0], parts[1])
            changed = True

    code_val = None
    for key in qp.keys():
        if _normalize_key(key) in {"codigo", "code", "cod", "sku", "id"}:
            code_val = qp.get(key)
            break
    if code_val is not None:
        qty_val = None
        for key in qp.keys():
            if _normalize_key(key) in {"quantidade", "qty", "q"}:
                qty_val = qp.get(key)
                break
        _add_code(cart, code_val, qty_val if qty_val is not None else 1)
        changed = True

    if "produto" in qp and "preco" in qp:
        nome = qp.get("produto")
        preco = qp.get("preco")
        qtd = qp.get("quantidade", 1)
        _add_item(cart, unquote(nome), preco, qtd)
        changed = True

    if changed:
        STORE[cid] = cart
        clean_url = url_for("index", cid=cid)
        resp = make_response(redirect(clean_url))
        resp.set_cookie("cid", cid, max_age=7 * 24 * 3600, samesite="Lax")
        return resp
    else:
        STORE[cid] = cart

    total = 0.0
    itens = []
    for produto, info in list(cart.items()):
        subtotal = float(info["preco"]) * int(info["qtd"])
        total += subtotal
        rm_href = f"?cid={quote(cid)}&rm={quote(produto)}" if cid else f"?rm={quote(produto)}"
        itens.append({"produto": produto, "qtd": info["qtd"], "subtotal": subtotal, "rm_href": rm_href})

    capital = total / 2 if total else 0.0
    cid_tip = cid or "meu123"
    return render_template("index.html", itens=itens, total=total, capital=capital, carrinho_vazio=(len(itens) == 0), cid_tip=cid_tip)

@app.get("/health")
def health():
    return {"status": "ok"}

# Para o Vercel
def handler(request, context):
    return handle_request(app, request)
