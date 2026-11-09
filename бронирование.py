import os
import json
from tkinter import *
from tkcalendar import DateEntry
from tkinter import messagebox, ttk
from datetime import date


root = Tk()
root.title("Бронирование залов")
root.geometry("1100x600")

base_orgs = ["ООО Ивент-Менеджмент", "МКПАО Яндекс", "ПАО Ростелеком", "ПАО Сбербанк", "ОАО РЖД"]

db_path = "bookings.json"
db = {}
cur_hall = None
cur_date = None
sel_start = None
sel_end = None

cell_w = 56
cell_h = 90
total_slots = 48
open_time = 9

dlg_w = 380
dlg_h = 150

def load_db():
    global db
    if not os.path.exists(db_path):
        db = {}
        return

    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.decoder.JSONDecodeError:
        db={}
        return

    if isinstance(data, dict):
        db = data
    else:
        db = {}

def save_db():
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def slot_to_time(slot):
    total =  open_time*60 + slot*15
    return f"{total//60:02d}:{total%60:02d}"

def is_selected(i):
    if sel_start is None:
        return False
    if sel_end is None:
        return i == sel_start
    return min(sel_start, sel_end) <= i <= max(sel_start, sel_end)

def overlaps(a, b, events):
    return any(ev["start"] <= b and a < ev["end"] for ev in events)

def draw_time():
    graph.delete("all")
    if not cur_hall or not cur_date:
        graph.create_text(200, 45, text="<<выберите зал, чтобы увидеть расписание>>", anchor="w",
                          font=("Arial", 10, "italic"))
        return

    events = db.get(cur_hall, {}).get(cur_date, [])
    for i in range(total_slots):
        x0, y0 = i*cell_w, 0
        x1, y1 = x0 + cell_w, y0 + cell_h

        is_busy = overlaps(i, i, events)
        if is_busy:
            color="red"
        elif is_selected(i):
            color="blue"
        else:
            color="green"
        graph.create_rectangle(x0, y0, x1, y1, fill=color, outline="white")

        graph.create_text(x0+28, y0+40, text=slot_to_time(i), font=("Arial", 8, "bold"), fill="white" if (is_busy or is_selected(i)) else "black")
    graph.configure(scrollregion=(0, 0, total_slots*cell_w, cell_h))

def update_calendar():
    listb.delete(0, END)
    if not cur_hall or not cur_date:
        return
    events = sorted(db.get(cur_hall, {}).get(cur_date, []), key=lambda event: event["start"])
    for event in events:
        listb.insert(END, f"{slot_to_time(event['start'])}-{slot_to_time(event['end'])} | {event['org']} - {event['name']}")

def on_canvas_click(e):
    global sel_start, sel_end
    if not cur_hall:
        return
    x = graph.canvasx(e.x)
    slot = int(x //cell_w)
    if not (0<=slot<total_slots):
        return

    events = sorted(db.get(cur_hall, {}).get(cur_date, []), key=lambda ev: ev["start"])
    for i, ev in enumerate(events):
        if ev["start"] <= slot < ev["end"]:
            listb.selection_clear(0, END)
            listb.selection_set(i)
            listb.see(i)
            sel_start = None
            sel_end = None
            draw_time()
            update_info()
            return

    if sel_start is None:
        sel_start = slot
        sel_end = None
    elif sel_end is None:
        a, b = min(slot, sel_start), max(slot, sel_start)
        if overlaps(a, b, events):
            messagebox.showwarning("Наложение", "Интервал пересекается с бронью")
            sel_start, sel_end = None, None
        else:
            sel_start, sel_end = a, b
    else:
        sel_start, sel_end = slot, None

    draw_time()
    update_info()


def select_hall(n):
    global cur_hall, cur_date, sel_start, sel_end
    cur_hall = f"Зал {n}"
    cur_date = data_entry.get_date().strftime("%Y-%m-%d")
    sel_start = None
    sel_end = None

    for i, btn in enumerate(hall_buttons, start=1):
        btn.configure(relief=SUNKEN if i == n else RAISED, bg = "lightgrey" if i==n else "SystemButtonFace")

    draw_time()
    update_calendar()
    update_info()

def date_change(event=None):
    global cur_date, sel_start, sel_end
    sel_start = None
    sel_end = None
    if cur_hall:
        cur_date = data_entry.get_date().strftime("%Y-%m-%d")
        update_calendar()
        draw_time()
        update_info()

def book():
    if not cur_hall:
        messagebox.showinfo("Бронь", "Сначала выберите зал")
        return
    if sel_start is None:
        messagebox.showinfo("Бронь", "Кликните по ячейке, чтобы выбрать время")
        return

    a = sel_start
    b = sel_end if sel_end is not None else sel_start
    start = min(a, b)
    end = max(a, b) +1

    def confirm():
        global sel_start, sel_end
        org = main_org_var.get().strip()
        name = name_var.get().strip()
        if not org or not name:
            messagebox.showwarning("Предупреждение", "Заполните оба окна", parent=dlg)
            return
        if org not in base_orgs:
            base_orgs.append(org)
        db.setdefault(cur_hall, {}).setdefault(cur_date, []).append({"start": start, "end": end, "org": org, "name": name})
        save_db()
        sel_start = None
        sel_end = None
        dlg.destroy()
        draw_time()
        update_calendar()
        update_info()
        main_org_var.set(org)
        select_org.configure(values=base_orgs)

    dlg = Toplevel(root)
    dlg.title("Бронирование")
    dlg.geometry(f"{dlg_w}x{dlg_h}")
    dlg.grab_set()
    dlg.transient(root)
    info = (f"Зал: {cur_hall}\nДата: {cur_date}\nВремя: {slot_to_time(start)} - {slot_to_time(end)}")
    Label(dlg, text=info, justify="left", font=("Consolas", 10)).place(x=12, y=10)
    Label(dlg, text="Название мероприятия:").place(x=12, y=60)
    name_var=StringVar()
    Entry(dlg, textvariable=name_var).place(x=12, y=80, width=dlg_w-24, height=24)
    Button(dlg, text="Утвердить", command=confirm).place(x=12, y=110, width=dlg_w-24, height=30)

def time_format(mins):
    h, m = mins//60, mins%60
    if h and m:
        return f"{h} ч. {m} мин."
    if h:
        return f"{h} ч."
    return f"{m} мин."


def update_info():
    if sel_start is None:
        info_var.set("Выберите интервал на таймлайне")
        return

    a, b = sorted((sel_start, sel_end if sel_end is not None else sel_start))

    mins = (b-a+1)*15
    time = f"{slot_to_time(a)} - {slot_to_time(b+1)}"

    org = main_org_var.get().strip()
    info_var.set(f"Организация: {org} | Время: {time} ({time_format(mins)})")


l = Frame(root, bg="lightgrey", bd=1)
l.place(x=10, y=10, relwidth=0.67, relheight=0.96)

Label(l, text="Выбор даты").place(x=10, y=10)
data_entry = DateEntry(l, date_pattern="dd-MM-yyyy", width=14, mindate=date.today())
data_entry.place(x=85, y=10)
data_entry.bind("<<DateEntrySelected>>", date_change)

main_org_var = StringVar(value=base_orgs[0])
Label(l, text="Выбор организации").place(x=240, y=10)
select_org = ttk.Combobox(l, values=base_orgs, textvariable=main_org_var, state="normal")
select_org.place(x=360, y=10, width=200)

info_var = StringVar(value="Выберите интервал на таймлайне")
Label(l, textvariable=info_var).place(x=10, y=165, width=716, height=20)

main_org_var.trace_add("write", lambda *args: update_info())
graph = Canvas(l, bg="white", highlightthickness=1)
graph.place(x=10, y=50, relwidth=1, height=90, width=-20)
graph.bind("<Button-1>", on_canvas_click)

scrollbar = Scrollbar(l, orient="horizontal", command=graph.xview)
scrollbar.place(x=10, y=144, relwidth=1, width=-20, height=16)
graph.configure(xscrollcommand=scrollbar.set)

Button(l, text="Забронировать", command=book).place(x=10, y=190, width=716, height=30)

hall_buttons = []
for i in range(5):
    butt = Button(l, text=f"Зал {i+1}", height=2, command=lambda n=i+1: select_hall(n))
    butt.place(relx=i/5, rely=1, y=-54, relwidth=0.2, width=-4, height=44)
    hall_buttons.append(butt)

r = Frame(root, bg="lightgrey", relief="groove")
r.place(relx=0.69, y=10, relwidth=0.29, relheight=0.96)

Label(r, text="Календарь мероприятий", bg="white", font=("Arial", 11, "bold")).place(x=10, y=10)

listb = Listbox(r, bg="white")
listb.place(x=8, y=40, relwidth=1, relheight=1, width=-30, height=-50)

scrollcalend = Scrollbar(r, orient="vertical", command=listb.yview)
scrollcalend.place(relx=1, x=-19, y=40, relheight=1, width=16, height=-50)
listb.configure(yscrollcommand=scrollcalend.set)

load_db()
draw_time()
update_info()
root.mainloop()