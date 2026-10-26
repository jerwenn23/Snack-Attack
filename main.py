import asyncio
import hashlib
import json
import random
import re
from pyscript import document, when
from js import localStorage, window

q = document.querySelector


def on(event_name, selector, fn):
    """Attach one handler to one selector.
    Each call gets its own small wrapper, so the same function (like filter_click,
    pick, refresh_total) can be used on many selectors without the PyScript
    'wrapper loop when unwrapping' error."""
    def handler(event):
        return fn(event)
    when(event_name, selector)(handler)


def money(n):
    return f"₱{n:,.2f}"


def load(key, default):
    try:
        raw = localStorage.getItem(key)
        return json.loads(raw) if raw else default
    except Exception:
        return default


def save(key, value):
    try:
        localStorage.setItem(key, json.dumps(value))
    except Exception:
        pass


# ---------------- Menu data (edit prices here) ----------------
def item(iid, name, img, desc, cat, sizes, flavors=(), flabel="Flavor", addons=()):
    return {"id": iid, "name": name, "img": img, "desc": desc, "cat": cat,
            "sizes": sizes, "flavors": list(flavors), "flabel": flabel, "addons": list(addons)}


FRIES, DRINKS, COMBO = "Fries & Potatoes", "Drinks", "Combos"
MENU = [
    item("sweet", "Crispy Sweet Potato Fries", "crispy-sweet-fries", "Crunchy sweet potato fries with your choice of sauce.",
         FRIES, [("Regular", 99)], ["Cheese sauce", "Spicy sauce", "Honey BBQ sauce", "No sauce"], "Sauce",
         [("Chicken bites", 20), ("Extra cheese", 10), ("Onion bits", 10), ("Corn", 10)]),
    item("plain", "Plain Fries", "plain-fries", "Golden crispy fries. Pick your flavor and size.",
         FRIES, [("Small", 50), ("Medium", 75), ("Large", 90)], ["Plain", "Cheese", "BBQ", "Sour cream", "Spicy"]),
    item("cheese", "Cheese Fries", "cheese-fries", "Hot fries covered in melty cheese.", FRIES, [("Regular", 120)]),
    item("spud", "Cheesy Spud", "cheesy-spud", "A creamy cheesy potato bowl with shredded cheese on top.", FRIES, [("Regular", 99)]),
    item("chicken", "Cheesy Chicken Fries", "cheesy-chicken-fries", "Fries topped with crispy chicken, melted cheese, and sauce.",
         FRIES, [("Regular", 145)]),
    item("tornado", "Tornado Potato", "tornado-potato", "Crispy spiral potato on a stick.",
         FRIES, [("Regular", 81)], ["Cheese", "BBQ", "Sour cream"]),
    item("straw", "Strawberry Lemonade", "strawberry-lemonade", "Sweet, sour, and icy cold.", DRINKS, [("Fixed size", 53)]),
    item("blue", "Blue Lemonade", "blue-lemonade", "Cool and refreshing.", DRINKS, [("Fixed size", 53)]),
    # Combo price: 145 + 53 = 198. Change 198 below if you want a discount.
    item("combo", "Cheesy Chicken Fries + Lemonade", "cheesy-chicken-fries", "Our Cheesy Chicken Fries with an ice-cold lemonade.",
         COMBO, [("Combo", 198)], ["Strawberry Lemonade", "Blue Lemonade"], "Lemonade"),
]
BEST = ["sweet", "chicken", "blue"]
TRENDING = [("Sweet potato", "sweet"), ("Cheesy", "cheesy"), ("Lemonade", "lemonade"), ("Tornado", "tornado"), ("Fries", "fries")]


def find(iid):
    return next(x for x in MENU if x["id"] == iid)


def price_text(it):
    low = min(p for _, p in it["sizes"])
    return ("From " if len(it["sizes"]) > 1 else "") + money(low)


def card_html(it):
    return (f'<div class="card" data-id="{it["id"]}"><div class="imgwrap"><img class="photo" src="images/{it["img"]}.jpg" alt="{it["name"]}"></div>'
            f'<h3>{it["name"]}</h3><p>{it["desc"]}</p><p class="price">{price_text(it)}</p>'
            f'<button data-id="{it["id"]}">Order now</button></div>')


# ---------------- Views and menu filters (click events) ----------------
flt = {"name": "All"}


def render_menu():
    name = flt["name"]
    if name == "All":
        html = ""
        for cat in [COMBO, FRIES, DRINKS]:
            html += f"<h2>{cat}</h2><div class=\"cards\">" + "".join(card_html(x) for x in MENU if x["cat"] == cat) + "</div>"
    else:
        items = [find(i) for i in BEST] if name == "Best Sellers" else [x for x in MENU if x["cat"] == name]
        html = "<div class=\"cards\">" + "".join(card_html(x) for x in items) + "</div>"
    q("#menu-grid").innerHTML = html
    for chip in document.querySelectorAll(".chip-f"):
        chip.classList.toggle("active", chip.getAttribute("data-filter") == name)


def show_view(name):
    for v in ["home", "menu", "contact"]:
        q(f"#view-{v}").classList.toggle("hidden", v != name)
        q(f'.nav-link[data-view="{v}"]').classList.toggle("active", v == name)
    window.scrollTo(0, 0)


def go_filter(name):
    flt["name"] = name
    render_menu()
    q("#search-panel").classList.add("hidden")
    show_view("menu")


def nav(event):
    show_view(event.currentTarget.getAttribute("data-view"))


def close_modal(event):
    q("#" + event.currentTarget.getAttribute("data-close")).classList.add("hidden")


def filter_click(event):
    t = event.target.closest("[data-filter]")
    if t:
        go_filter(t.getAttribute("data-filter"))


async def toast(text):
    t = q("#toast")
    t.innerText = text
    t.classList.remove("hidden")
    await asyncio.sleep(2)
    t.classList.add("hidden")


def say(text):
    asyncio.ensure_future(toast(text))


on("click", "[data-view]", nav)
on("click", "[data-close]", close_modal)
on("click", "#filters", filter_click)
on("click", "#s-cats", filter_click)

# ---------------- Cart ----------------
cart = load("sa_cart", [])


def cart_total():
    return sum(it["line"] for it in cart)


def render_cart():
    ul = q("#cart-list")
    if not cart:
        ul.innerHTML = "<li>Your cart is empty. Pick a snack from the menu!</li>"
    else:
        rows = ""
        for i, it in enumerate(cart):
            info = " · ".join(x for x in [it["size"], it["flavor"], ", ".join(it["addons"])] if x)
            rows += (f'<li class="row"><span style="display:flex;align-items:center"><img src="images/{it.get("img", "cheese-fries")}.jpg" alt="">'
                     f'<span><b>{it["name"]}</b><br><small>{info}</small></span></span>'
                     f'<span><button data-act="minus" data-i="{i}">−</button> {it["qty"]} '
                     f'<button data-act="plus" data-i="{i}">+</button> <b>{money(it["line"])}</b> '
                     f'<button data-act="del" data-i="{i}">✕</button></span></li>')
        ul.innerHTML = rows
    q("#cart-total").innerText = money(cart_total())
    q("#co-total").innerText = money(cart_total())
    q("#cart-count").innerText = str(sum(it["qty"] for it in cart))


def cart_action(event):
    act = event.target.getAttribute("data-act")
    if act is None:
        return
    i = int(event.target.getAttribute("data-i"))
    if act == "del":
        cart.pop(i)
    elif act == "plus":
        cart[i]["qty"] += 1
    elif act == "minus":
        cart[i]["qty"] -= 1
        if cart[i]["qty"] < 1:
            cart.pop(i)
    for it in cart:
        it["line"] = it["unit"] * it["qty"]
    save("sa_cart", cart)
    render_cart()


def open_cart(event):
    render_cart()
    q("#cart-modal").classList.remove("hidden")


on("click", "#cart-list", cart_action)
on("click", "#open-cart", open_cart)

# ---------------- Item popup: size, flavor, quantity ----------------
cur = {"item": None, "qty": 1}


def choice():
    it = cur["item"]
    sel = q("#m-size")
    opt = sel.options.item(sel.selectedIndex)
    base = int(opt.dataset.price)
    flavor = q("#m-flavor").value if it["flavors"] else ""
    addons, extra = [], 0
    for box in document.querySelectorAll("#m-addons .addon"):
        if box.checked:
            addons.append(box.value)
            extra += int(box.dataset.price)
    unit = base + extra
    return {"name": it["name"], "img": it["img"], "size": opt.value, "flavor": flavor, "addons": addons,
            "qty": cur["qty"], "unit": unit, "line": unit * cur["qty"]}


def refresh_total(event=None):
    q("#m-total").innerText = money(choice()["line"])


def open_item(iid):
    it = find(iid)
    cur["item"], cur["qty"] = it, 1
    q("#m-img").src = f'images/{it["img"]}.jpg'
    q("#m-name").innerText = it["name"]
    q("#m-desc").innerText = it["desc"]
    q("#m-size").innerHTML = "".join(f'<option value="{s}" data-price="{p}">{s} ({money(p)})</option>' for s, p in it["sizes"])
    q("#m-flv-wrap").style.display = "block" if it["flavors"] else "none"
    q("#m-flabel").innerText = it["flabel"]
    q("#m-flavor").innerHTML = "".join(f"<option>{f}</option>" for f in it["flavors"])
    q("#m-add-wrap").style.display = "block" if it["addons"] else "none"
    q("#m-addons").innerHTML = "".join(
        f'<label><input type="checkbox" class="addon" value="{n}" data-price="{p}"> {n} (+{money(p)})</label>' for n, p in it["addons"])
    q("#m-qty").innerText = "1"
    refresh_total()
    q("#search-panel").classList.add("hidden")
    q("#item-modal").classList.remove("hidden")


def pick(event):
    t = event.target.closest("[data-id]")
    if t:
        open_item(t.getAttribute("data-id"))


def qty_minus(event):
    if cur["qty"] > 1:
        cur["qty"] -= 1
        q("#m-qty").innerText = str(cur["qty"])
        refresh_total()


def qty_plus(event):
    if cur["qty"] < 50:
        cur["qty"] += 1
        q("#m-qty").innerText = str(cur["qty"])
        refresh_total()


def add_to_cart(event):
    cart.append(choice())
    save("sa_cart", cart)
    render_cart()
    q("#item-modal").classList.add("hidden")
    say("Added to cart ✓")


for sel_id in ["#best-grid", "#menu-grid", "#s-results", "#promo"]:
    on("click", sel_id, pick)
for sel_id in ["#m-size", "#m-flavor", "#m-addons"]:
    on("change", sel_id, refresh_total)
on("click", "#q-minus", qty_minus)
on("click", "#q-plus", qty_plus)
on("click", "#add-cart", add_to_cart)

# ---------------- Checkout: GCash, Maya, or Cash ----------------
def go_checkout(event):
    if not cart:
        say("Your cart is empty")
        return
    q("#cart-modal").classList.add("hidden")
    q("#msg").innerText = ""
    q("#sms").classList.add("hidden")
    q("#gcash").classList.add("hidden")
    render_cart()
    q("#checkout-modal").classList.remove("hidden")


def back_to_cart(event):
    q("#checkout-modal").classList.add("hidden")
    q("#cart-modal").classList.remove("hidden")


def place_order(event):
    msg = q("#msg")
    name = q("#cust").value.strip()
    mobile = q("#mobile").value.strip().replace(" ", "")
    msg.className = "err"
    if not cart:
        msg.innerText = "Your cart is empty."
        return
    if not name:
        msg.innerText = "Please enter your name for pickup."
        return
    if not re.fullmatch(r"(09|\+639)\d{9}", mobile):
        msg.innerText = "Enter a valid mobile number (09XXXXXXXXX or +639XXXXXXXXX)."
        return
    msg.innerText = ""
    method = q('input[name="pay"]:checked').value
    if method == "Cash":
        finish_order("Cash")
    else:
        q("#pay-title").innerText = method
        q("#qr-img").src = "images/qr-maya.jpg" if method == "Maya" else "images/qr-gcash.jpg"
        q("#qr-img").alt = f"{method} QR code"
        q("#qr-app").innerText = method
        q("#gcash").classList.toggle("maya", method == "Maya")
        q("#pay-amt").innerText = money(cart_total())
        q("#ref").value = ""
        q("#gcash").classList.remove("hidden")


def cancel_pay(event):
    q("#gcash").classList.add("hidden")


LOC = "outside Punta Princesa Elementary & Night School, Dela Cerna"


def pay(event):
    method = q('input[name="pay"]:checked').value
    ref = q("#ref").value.strip()
    if len(ref) < 6:
        q("#msg").className = "err"
        q("#msg").innerText = "Enter the reference number from your payment receipt."
        return
    finish_order(method, ref)


def order_text(order_no, name, mobile, method, ref, notes):
    lines = [f"Snack Attack order {order_no}", f"Name: {name}", f"Mobile: {mobile}"]
    for it in cart:
        info = ", ".join(x for x in [it["size"], it["flavor"], ", ".join(it["addons"])] if x)
        lines.append(f'{it["qty"]}x {it["name"]}' + (f" ({info})" if info else "") + f' - {money(it["line"])}')
    lines.append(f"Total: {money(cart_total())}")
    lines.append("Payment: Cash at pickup" if method == "Cash" else f"Payment: {method}, ref {ref}")
    if notes:
        lines.append(f"Notes: {notes}")
    return "\n".join(lines)


def finish_order(method, ref=""):
    name = q("#cust").value.strip()
    mobile = q("#mobile").value.strip().replace(" ", "")
    notes = q("#notes").value.strip()
    order_no = f"SA-{random.randint(1000, 9999)}"
    text = order_text(order_no, name, mobile, method, ref, notes)
    total = money(cart_total())
    how = "pay cash at pickup" if method == "Cash" else f"paid with {method} (ref {ref}), we will confirm your payment"
    msg = q("#msg")
    msg.className = "ok"
    msg.innerText = (f"Order {order_no} placed! Thank you, {name}. Total {total}, {how}. "
                     f"Pick it up {LOC}, 10:00 AM – 9:00 PM. Tap the button below to text us your order so we can start.")
    sms = q("#sms")
    sms.href = "sms:09266636333?&body=" + window.encodeURIComponent(text)
    sms.classList.remove("hidden")
    q("#gcash").classList.add("hidden")
    cart.clear()
    save("sa_cart", cart)
    render_cart()


on("click", "#go-checkout", go_checkout)
on("click", "#back-cart", back_to_cart)
on("click", "#place", place_order)
on("click", "#cancel-pay", cancel_pay)
on("click", "#pay", pay)

# ---------------- Search panel ----------------
def row_html(it):
    return (f'<div class="srow" data-id="{it["id"]}"><img src="images/{it["img"]}.jpg" alt="">'
            f'<div><b>{it["name"]}</b><br>{price_text(it)}</div></div>')


def render_search(text=""):
    t = text.strip().lower()
    if t:
        q("#s-default").classList.add("hidden")
        found = [x for x in MENU if t in x["name"].lower() or t in x["desc"].lower() or t in x["cat"].lower()]
        q("#s-title").innerText = f"Results ({len(found)})"
    else:
        q("#s-default").classList.remove("hidden")
        found = [find(i) for i in BEST]
        q("#s-title").innerText = "Best Sellers"
    q("#s-results").innerHTML = "".join(row_html(x) for x in found) or "<p>No snacks found. Try another word.</p>"


def open_search(event):
    q("#search-panel").classList.remove("hidden")
    q("#s-input").focus()


def on_search_input(event):
    render_search(q("#s-input").value)


def chip_click(event):
    t = event.target.closest("[data-q]")
    if t:
        q("#s-input").value = t.getAttribute("data-q")
        render_search(t.getAttribute("data-q"))


on("click", "#open-search", open_search)
on("input", "#s-input", on_search_input)
on("click", "#s-chips", chip_click)

# ---------------- Log in / Sign up (showcase) ----------------
accounts = load("sa_accounts", {})
user = load("sa_user", None)
EMAIL = r"[^@\s]+@[^@\s]+\.[^@\s]+"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def update_user_ui():
    q("#open-login").innerText = f"👤 {user['name']} (Log out)" if user else "👤 Log in"
    if user and not q("#cust").value:
        q("#cust").value = user["name"]


def show_pane(which):
    q("#login-pane").classList.toggle("hidden", which != "login")
    q("#signup-pane").classList.toggle("hidden", which != "signup")
    q("#l-msg").innerText = ""


def open_login(event):
    global user
    if user:
        user = None
        save("sa_user", None)
        update_user_ui()
        say("Logged out")
        return
    show_pane("login")
    q("#login-modal").classList.remove("hidden")


def do_login(event):
    global user
    email = q("#l-email").value.strip().lower()
    pw = q("#l-pass").value
    msg = q("#l-msg")
    msg.className = "err"
    if not re.fullmatch(EMAIL, email) or not pw:
        msg.innerText = "Enter your email and password."
    elif email not in accounts:
        msg.innerText = "No account with that email yet. Create one below."
    elif accounts[email]["hash"] != sha(pw):
        msg.innerText = "Wrong password. Try again."
    else:
        user = {"name": accounts[email]["name"], "email": email}
        save("sa_user", user)
        q("#login-modal").classList.add("hidden")
        update_user_ui()
        say(f"Welcome back, {user['name']}!")


def do_signup(event):
    global user
    name = q("#s-name").value.strip()
    email = q("#s-email").value.strip().lower()
    pw = q("#s-pass").value
    msg = q("#l-msg")
    msg.className = "err"
    if not name or not re.fullmatch(EMAIL, email):
        msg.innerText = "Enter your name and a valid email."
    elif len(pw) < 6:
        msg.innerText = "Password must be at least 6 characters."
    elif email in accounts:
        msg.innerText = "That email already has an account. Log in instead."
    else:
        accounts[email] = {"name": name, "hash": sha(pw)}
        save("sa_accounts", accounts)
        user = {"name": name, "email": email}
        save("sa_user", user)
        q("#login-modal").classList.add("hidden")
        update_user_ui()
        say(f"Account created. Hi, {name}!")


on("click", "#open-login", open_login)
on("click", "#do-login", do_login)
on("click", "#do-signup", do_signup)
on("click", "#to-signup", lambda e: show_pane("signup"))
on("click", "#to-login", lambda e: show_pane("login"))
on("click", "#forgot", lambda e: say("Password reset is a showcase feature"))
on("click", "#pay-card", lambda e: say("Choose GCash, Maya, or Cash at checkout"))
on("click", "#badge-pay", lambda e: say("Pay with GCash, Maya, or Cash"))


# ---------------- Contact form ----------------
def send_message(event):
    name = q("#c-name").value.strip()
    text = q("#c-text").value.strip()
    out = q("#c-msg")
    if not name or not text:
        out.className = "err"
        out.innerText = "Please enter your name and a message."
        return
    out.className = "ok"
    out.innerText = f"Thank you, {name}! We got your message."
    q("#c-text").value = ""


on("click", "#send-msg", send_message)

# ---------------- Start ----------------
render_menu()
q("#best-grid").innerHTML = "".join(card_html(find(i)) for i in BEST)
q("#s-chips").innerHTML = "".join(f'<button class="chip" data-q="{k}">{lbl}</button>' for lbl, k in TRENDING)
render_search("")
render_cart()
update_user_ui()
