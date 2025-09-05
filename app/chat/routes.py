from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.chat import bp
from app import db
from app.models import ChatMessage, ChatRoom, AuditLog
from datetime import datetime

@bp.route('/')
@login_required
def index():
    room_id = request.args.get('room', type=int)
    rooms_q = ChatRoom.query
    if not current_user.is_admin:
        rooms_q = rooms_q.filter((ChatRoom.is_admin_only.is_(False)) | (ChatRoom.is_admin_only.is_(None)))
    rooms = rooms_q.order_by(ChatRoom.name.asc()).all()
    active_room = None
    if room_id:
        active_room = next((r for r in rooms if r.id == room_id), None)
    if not active_room and rooms:
        active_room = rooms[0]
    return render_template('chat/index.html', rooms=rooms, active_room=active_room)

@bp.route('/api/messages')
@login_required
def api_messages():
    room_id = request.args.get('room', type=int)
    q = ChatMessage.query
    if room_id:
        q = q.filter(ChatMessage.room_id==room_id)
    if not current_user.is_admin:
        # Admin-only Räume ausfiltern
        q = q.join(ChatRoom, ChatRoom.id==ChatMessage.room_id).filter((ChatRoom.is_admin_only.is_(False)) | (ChatRoom.is_admin_only.is_(None)))
    rows = q.order_by(ChatMessage.id.desc()).limit(200).all()[::-1]
    return jsonify([{ 'id':m.id,'user_id':m.user_id,'content':m.content,'created_at':m.created_at.isoformat(),'room_id':m.room_id,'username':m.sender.username if m.sender else None } for m in rows])

@bp.route('/api/rooms', methods=['POST'])
@login_required
def api_create_room():
    if not current_user.is_admin:
        return jsonify({'error':'forbidden'}),403
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error':'name required'}),400
    is_admin_only = bool(data.get('is_admin_only'))
    if ChatRoom.query.filter_by(name=name).first():
        return jsonify({'error':'exists'}),409
    r = ChatRoom(name=name, created_by=current_user.id, is_admin_only=is_admin_only)
    db.session.add(r)
    db.session.add(AuditLog(actor_id=current_user.id, action='chat_room_create', target_type='chat_room', target_id='new', details=name))
    db.session.commit()
    return jsonify({'id':r.id,'name':r.name,'is_admin_only':r.is_admin_only})

@bp.route('/api/rooms/<int:room_id>/clear', methods=['POST'])
@login_required
def api_clear_room(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if room.is_admin_only and not current_user.is_admin:
        return jsonify({'error':'forbidden'}),403
    ChatMessage.query.filter_by(room_id=room.id).delete()
    db.session.add(AuditLog(actor_id=current_user.id, action='chat_room_clear', target_type='chat_room', target_id=str(room.id), details='cleared'))
    db.session.commit()
    return jsonify({'cleared':True})
    expenses = sum(e.amount for e in q if e.kind=='expense')
    balance = incomes - expenses

    # Kategorien & Summen nur Ausgaben
    cat_base = db.session.query(Category.id, Category.name, Category.color, Category.monthly_budget, func.sum(Expense.amount).label('spent')) \
        .outerjoin(Expense, (Expense.category_id==Category.id) & (Expense.date>=month_start) & (Expense.date<next_month) & (Expense.kind=='expense'))
    if current_user.is_admin:
        if user_id_param:
            cat_base = cat_base.filter(or_(Category.user_id==user_id_param, Category.user_id.is_(None))) \
                                 .filter(or_(Expense.user_id==user_id_param, Expense.user_id.is_(None)))
    else:
        cat_base = cat_base.filter(or_(Category.user_id==current_user.id, Category.user_id.is_(None))) \
                             .filter(or_(Expense.user_id==current_user.id, Expense.user_id.is_(None)))
    cat_rows = cat_base.group_by(Category.id, Category.name, Category.color, Category.monthly_budget).all()
    categories = [{
        'id': c[0], 'name': c[1], 'color': c[2], 'budget': c[3], 'spent': float(c[4] or 0.0),
        'percent': (float(c[4] or 0.0)/c[3]*100) if c[3] else None
    } for c in cat_rows]

    return render_template('finance/index.html',
        month_incomes=incomes,
        month_expenses=expenses,
        month_balance=balance,
        categories=categories,
        currency=CURRENCY_SYMBOL,
        is_admin=current_user.is_admin,
        viewed_user_id=user_id_param
    )

@bp.route('/new')
@login_required
def new_dashboard():
    """Neues vereinfachtes Finanz-Dashboard (Beta)."""
    return render_template('finance/dashboard_new.html')

def _auto_generate_recurring():
    """Erzeuge fehlende Instanzen für aktive Wiederkehrende Buchungen bis heute.
    Admins: generiere für alle aktiven, um konsistente Anzeige zu gewährleisten.
    """
    today = date.today()
    if current_user.is_authenticated and current_user.is_admin:
        recs = RecurringTransaction.query.filter_by(active=True).all()
    else:
        recs = RecurringTransaction.query.filter_by(active=True, user_id=current_user.id).all()
    for r in recs:
        last = r.last_generated_date or (r.start_date if r.start_date <= today else None)
        if not last:
            continue
        # Schleife: nächstes Datum generieren
        safety = 0
        while True:
            if r.frequency == 'monthly':
                year = last.year + (1 if last.month==12 else 0)
                month = 1 if last.month==12 else last.month+1
                day = min(last.day, 28 if month==2 else 30 if month in (4,6,9,11) and last.day>30 else last.day)
                try:
                    nxt = date(year, month, day)
                except ValueError:
                    nxt = date(year, month, 28)
            elif r.frequency == 'weekly':
                from datetime import timedelta as _td
                nxt = last + _td(days=7)
            elif r.frequency == 'yearly':
                try:
                    nxt = date(last.year+1, last.month, last.day)
                except ValueError:
                    nxt = date(last.year+1, last.month, 28)
            else:
                break
            if nxt > today:
                break
            # Erstellen falls nicht vorhanden (gleicher Tag & Betrag & Beschreibung)
            exists = Expense.query.filter_by(user_id=r.user_id, date=nxt, amount=r.amount, description=r.description, kind=r.kind, account_id=r.account_id).first()
            if not exists:
                e = Expense(amount=r.amount, description=r.description, category=r.category, category_id=r.category_id,
                            date=nxt, user_id=r.user_id, kind=r.kind, account_id=r.account_id)
                db.session.add(e)
                if r.account_id:
                    acc = Account.query.get(r.account_id)
                    if acc:
                        if r.kind=='income':
                            acc.balance += r.amount
                        else:
                            if acc.balance >= r.amount or acc.allow_negative:
                                acc.balance -= r.amount
                            else:
                                pass
            r.last_generated_date = nxt
            last = nxt
            safety += 1
            if safety>60:  # Schutz gegen Endlosschleife
                break
    db.session.commit()

@bp.route('/api/items', methods=['GET'])
@login_required
def list_items():
    kind = request.args.get('kind')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    q_param = request.args.get('q', '').strip()
    start_d = request.args.get('start')
    end_d = request.args.get('end')
    page = max(1, request.args.get('page', type=int) or 1)
    page_size = min(200, request.args.get('page_size', type=int) or 50)

    q = Expense.query
    user_id_param = None
    if current_user.is_admin:
        user_id_param = request.args.get('user_id', type=int)
        if user_id_param:
            q = q.filter(Expense.user_id==user_id_param)
    else:
        q = q.filter(Expense.user_id==current_user.id)

    if kind in ('income','expense'):
        q = q.filter(Expense.kind==kind)
    if year:
        q = q.filter(func.extract('year', Expense.date)==year)
    if month:
        q = q.filter(func.extract('month', Expense.date)==month)
    if start_d:
        try: q = q.filter(Expense.date >= datetime.fromisoformat(start_d).date())
        except Exception: pass
    if end_d:
        try: q = q.filter(Expense.date <= datetime.fromisoformat(end_d).date())
        except Exception: pass
    if q_param:
        like = f"%{q_param}%"
        q = q.filter(or_(Expense.description.ilike(like), Expense.category.ilike(like)))
    total = q.count()
    pages = ceil(total / page_size) if total else 1
    # Optional Account-Namen map für Ausgabe
    items = q.order_by(Expense.date.desc(), Expense.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    account_ids = {x.account_id for x in items if x.account_id}
    account_map = {}
    if account_ids:
        for a in Account.query.filter(Account.id.in_(account_ids)).all():
            account_map[a.id] = a.name
    return jsonify({
        'items': [{
            'id': x.id,
            'date': x.date.isoformat(),
            'kind': x.kind,
            'category': x.category,
            'categoryId': x.category_id,
            'rawAmount': x.amount,
            'description': x.description,
            'paymentMethod': x.payment_method,
            'notes': x.notes,
            'accountId': x.account_id,
            'accountName': account_map.get(x.account_id),
            'userId': x.user_id
        } for x in items],
        'meta': {'page':page,'pages':pages,'total':total,'is_admin':current_user.is_admin,'filtered_user_id':user_id_param}
    })

# Alias für neue UI
@bp.route('/api/transactions', methods=['GET'])
@login_required
def transactions_alias():
    return list_items()

@bp.route('/api/item', methods=['POST'])
@login_required
def create_item():
    data = request.get_json() or {}
    amount = _parse_float(data.get('amount'))
    err = _validate_amount(amount)
    if err: return jsonify({'error':err}),400
    kind = data.get('kind','expense')
    if kind not in ('income','expense'):
        return jsonify({'error':'kind ungültig'}),400
    try:
        d = datetime.fromisoformat(data.get('date')).date()
    except Exception:
        return jsonify({'error':'Datum ungültig'}),400
    cat_id = data.get('categoryId')
    category_name = (data.get('category') or '').strip()[:64] or 'Allgemein'
    # Konto optional
    account_id = data.get('accountId')
    acc = None
    if account_id is not None:
        try:
            account_id = int(account_id)
            acc = Account.query.get(account_id)
            if not acc:
                return jsonify({'error':'Konto nicht gefunden'}),404
            if not (current_user.is_admin or acc.user_id in (None, current_user.id)):
                return jsonify({'error':'Keine Berechtigung für Konto'}),403
        except Exception:
            return jsonify({'error':'Ungültiges Konto'}),400
    e = Expense(amount=amount,
                description=(data.get('description') or '').strip() or '—',
                category=category_name,
                date=d,
                user_id=current_user.id,
                kind=kind,
                category_id=cat_id if isinstance(cat_id, int) else None,
                account_id=acc.id if acc else None)
    # NEU Felder
    e.payment_method = (data.get('paymentMethod') or '').strip()[:30] or None
    e.notes = (data.get('notes') or '').strip() or None
    db.session.add(e)
    # Kontostand aktualisieren
    if acc:
        if kind=='income':
            acc.balance += amount
        else:
            if acc.balance < amount and not acc.allow_negative:
                return jsonify({'error':'Nicht genügend Guthaben im Konto'}),400
            acc.balance -= amount

    # Neu: optional direkt wiederkehrend anlegen
    if data.get('makeRecurring'):
        freq = data.get('recFrequency')
        if freq not in ('weekly','monthly','yearly'):
            return jsonify({'error':'recFrequency ungültig'}),400
        from app.models import RecurringTransaction  # lazy import
        r = RecurringTransaction(
            user_id=current_user.id,
            description=e.description,
            amount=e.amount,
            kind=kind,
            category=category_name,
            category_id=e.category_id,
            start_date=d,
            frequency=freq,
            last_generated_date=d,   # verhindert Doppelanlage beim nächsten _auto_generate_recurring()
            active=True
        )
        db.session.add(r)

    db.session.add(AuditLog(actor_id=current_user.id, action='finance_create', target_type='expense', target_id=str(e.id), details=f'amount={e.amount};kind={e.kind};account={e.account_id}'))
    db.session.commit()
    _snapshot_accounts([e.account_id])
    return jsonify({'id': e.id, 'recurring': bool(data.get('makeRecurring'))})

@bp.route('/api/item/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    data = request.get_json() or {}
    e = Expense.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    amount_new = _parse_float(data.get('amount')) if 'amount' in data else e.amount
    if 'amount' in data:
        err = _validate_amount(amount_new)
        if err: return jsonify({'error':err}),400
    old_amount = e.amount
    old_kind = e.kind
    old_account_id = e.account_id
    # Neues Konto (optional)
    new_account_id = data.get('accountId', old_account_id)
    acc_new = None
    if new_account_id is not None:
        try:
            new_account_id = int(new_account_id)
            acc_new = Account.query.get(new_account_id)
            if acc_new and not (current_user.is_admin or acc_new.user_id in (None, current_user.id)):
                return jsonify({'error':'Keine Berechtigung für neues Konto'}),403
        except Exception:
            return jsonify({'error':'Ungültiges Konto'}),400
    if 'description' in data:
        e.description = (data.get('description') or '').strip() or '—'
    if 'category' in data:
        e.category = (data.get('category') or 'Allgemein').strip()[:64]
    if 'categoryId' in data:
        cid = data.get('categoryId')
        e.category_id = cid if isinstance(cid, int) else None
    if 'date' in data:
        try:
            e.date = datetime.fromisoformat(data.get('date')).date()
        except Exception:
            pass
    if 'kind' in data and data.get('kind') in ('income','expense'):
        e.kind = data.get('kind')
    if 'amount' in data:
        e.amount = amount_new
    if 'accountId' in data:
        e.account_id = acc_new.id if acc_new else None
    # Kontostände anpassen falls nötig
    changed = (old_account_id != e.account_id) or (old_amount != e.amount) or (old_kind != e.kind)
    if changed:
        acc_old = Account.query.get(old_account_id) if old_account_id else None
        if acc_old:
            if old_kind=='income':
                acc_old.balance -= old_amount
            else:
                acc_old.balance += old_amount
        if e.account_id:
            acc_new2 = Account.query.get(e.account_id)
            if acc_new2:
                if e.kind=='income':
                    acc_new2.balance += e.amount
                else:
                    if acc_new2.balance < e.amount and not acc_new2.allow_negative:
                        return jsonify({'error':'Nicht genügend Guthaben im Zielkonto'}),400
                    acc_new2.balance -= e.amount
    # NEU sicherstellen
    e.payment_method = (data.get('paymentMethod') or '').strip()[:30] or None
    e.notes = (data.get('notes') or '').strip() or None
    db.session.add(AuditLog(actor_id=current_user.id, action='finance_update', target_type='expense', target_id=str(e.id), details=f'changed={changed}'))
    db.session.commit()
    if changed:
        _snapshot_accounts([old_account_id, e.account_id])
    return jsonify({'status':'ok'})

@bp.route('/api/item/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    e = Expense.query.get_or_404(item_id)
    if e.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error':'Unauthorized'}),403
    if e.account_id:
        acc = Account.query.get(e.account_id)
        if acc:
            if e.kind=='income':
                acc.balance -= e.amount
            else:
                acc.balance += e.amount
    db.session.add(AuditLog(actor_id=current_user.id, action='finance_delete', target_type='expense', target_id=str(e.id), details=f'amount={e.amount};kind={e.kind}'))
    acc_id_tmp = e.account_id
    db.session.delete(e)
    db.session.commit()
    _snapshot_accounts([acc_id_tmp])
    return jsonify({'status':'deleted'})

@bp.route('/api/item/<int:item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    e = Expense.query.get_or_404(item_id)
    if e.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error':'Unauthorized'}),403
    acc = Account.query.get(e.account_id) if e.account_id else None
    return jsonify({'id':e.id,'date':e.date.isoformat(),'kind':e.kind,'category':e.category,'categoryId':e.category_id,'amount':e.amount,'description':e.description,'paymentMethod':e.payment_method,'notes':e.notes,'accountId':e.account_id,'accountName':acc.name if acc else None})

@bp.route('/api/summary')
@login_required
def summary():
    year = request.args.get('year', type=int) or date.today().year
    user_id_param = request.args.get('user_id', type=int) if current_user.is_admin else None

    income_expr = func.sum(case((Expense.kind == 'income', Expense.amount), else_=0)).label('income')
    expense_expr = func.sum(case((Expense.kind == 'expense', Expense.amount), else_=0)).label('expense')

    q = db.session.query(
        extract('month', Expense.date).label('month'),
        income_expr,
        expense_expr
    ).filter(extract('year', Expense.date) == year)
    if current_user.is_admin:
        if user_id_param:
            q = q.filter(Expense.user_id==user_id_param)
    else:
        q = q.filter(Expense.user_id==current_user.id)
    q = q.group_by('month').order_by('month')
    rows = q.all()
    data = [{'month': int(r.month), 'income': float(r.income or 0), 'expense': float(r.expense or 0)} for r in rows]
    return jsonify({'year': year, 'months': data, 'is_admin': current_user.is_admin, 'filtered_user_id': user_id_param})

# ---------------- Categories API -----------------
@bp.route('/api/categories', methods=['GET'])
@login_required
def list_categories():
    cats = Category.query.filter(or_(Category.user_id==current_user.id, Category.user_id.is_(None))).order_by(Category.name.asc()).all()
    return jsonify([
        {'id': c.id, 'name': c.name, 'color': c.color, 'budget': c.monthly_budget, 'category_type': c.category_type or 'expense'} for c in cats
    ])

@bp.route('/api/category', methods=['POST'])
@login_required
def create_category():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error':'Name erforderlich'}),400
    c = Category(name=name[:64], color=data.get('color'), monthly_budget=_parse_float(data.get('budget')) or None, user_id=current_user.id)
    db.session.add(c)
    db.session.commit()
    return jsonify({'id': c.id})

@bp.route('/api/category/<int:cat_id>', methods=['PUT'])
@login_required
def update_category(cat_id):
    c = Category.query.get_or_404(cat_id)
    if c.user_id not in (None, current_user.id) and not current_user.is_admin:
        return jsonify({'error':'Unauthorized'}),403
    data = request.get_json() or {}
    if 'name' in data:
        nn = (data.get('name') or '').strip()
        if nn: c.name = nn[:64]
    if 'color' in data:
        c.color = data.get('color')
    if 'budget' in data:
        b = _parse_float(data.get('budget'))
        c.monthly_budget = b if b>0 else None
    db.session.commit()
    return jsonify({'status':'ok'})

@bp.route('/api/category/<int:cat_id>', methods=['DELETE'])
@login_required
def delete_category(cat_id):
    c = Category.query.get_or_404(cat_id)
    if c.user_id not in (None, current_user.id) and not current_user.is_admin:
        return jsonify({'error':'Unauthorized'}),403
    # Optional: Expenses behalten Kategorie-Name als Text
    for e in c.expenses:
        e.category_id = None
    db.session.delete(c)
    db.session.commit()
    return jsonify({'status':'deleted'})

# ---------------- Recurring API ------------------
@bp.route('/api/recurring', methods=['GET'])
@login_required
def list_recurring():
    q = RecurringTransaction.query
    user_id_param = None
    if current_user.is_admin:
        user_id_param = request.args.get('user_id', type=int)
        if user_id_param:
            q = q.filter(RecurringTransaction.user_id==user_id_param)
    else:
        q = q.filter(RecurringTransaction.user_id==current_user.id)
    recs = q.order_by(RecurringTransaction.active.desc(), RecurringTransaction.id.desc()).all()
    return jsonify([
        {
            'id': r.id, 'description': r.description, 'amount': r.amount, 'kind': r.kind,
            'category': r.category, 'categoryId': r.category_id, 'startDate': r.start_date.isoformat(),
            'frequency': r.frequency, 'lastGenerated': r.last_generated_date.isoformat() if r.last_generated_date else None,
            'active': r.active, 'userId': r.user_id
        } for r in recs
    ])

@bp.route('/api/recurring', methods=['POST'])
@login_required
def create_recurring():
    data = request.get_json() or {}
    desc = (data.get('description') or '').strip()
    amt = _parse_float(data.get('amount'))
    freq = data.get('frequency')
    if not desc or amt<=0 or freq not in ('weekly','monthly','yearly'):
        return jsonify({'error':'Ungültige Daten'}),400
    try:
        sd = datetime.fromisoformat(data.get('startDate')).date()
    except Exception:
        return jsonify({'error':'Startdatum ungültig'}),400
    acc_id = data.get('accountId')
    if acc_id is not None:
        try:
            acc_id = int(acc_id)
            acc = Account.query.get(acc_id)
            if acc and not (current_user.is_admin or acc.user_id in (None, current_user.id)):
                return jsonify({'error':'Keine Berechtigung für Konto'}),403
        except Exception:
            return jsonify({'error':'Ungültiges Konto'}),400
    r = RecurringTransaction(user_id=current_user.id, description=desc, amount=amt, kind=data.get('kind','expense'),
                             category=(data.get('category') or 'Allgemein'), category_id=data.get('categoryId'),
                             start_date=sd, frequency=freq, account_id=acc_id)
    db.session.add(r)
    db.session.add(AuditLog(actor_id=current_user.id, action='recurring_create', target_type='recurring', target_id=str(r.id), details=f'amount={r.amount};freq={r.frequency}'))
    db.session.commit()
    return jsonify({'id': r.id})

@bp.route('/api/recurring/<int:rid>', methods=['PUT'])
@login_required
def update_recurring(rid):
    r = RecurringTransaction.query.get_or_404(rid)
    if r.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error':'Unauthorized'}),403
    data = request.get_json() or {}
    if 'description' in data:
        d = (data.get('description') or '').strip()
        if d: r.description = d
    if 'amount' in data:
        v = _parse_float(data.get('amount'))
        if v>0: r.amount = v
    if 'kind' in data and data.get('kind') in ('income','expense'):
        r.kind = data.get('kind')
    if 'frequency' in data and data.get('frequency') in ('weekly','monthly','yearly'):
        r.frequency = data.get('frequency')
    if 'category' in data:
        r.category = (data.get('category') or 'Allgemein')
    if 'categoryId' in data:
        r.category_id = data.get('categoryId')
    if 'startDate' in data:
        try: r.start_date = datetime.fromisoformat(data.get('startDate')).date()
        except Exception: pass
    if 'active' in data:
        r.active = bool(data.get('active'))
    if 'accountId' in data:
        acc_id = data.get('accountId')
        if acc_id is None:
            r.account_id = None
        else:
            try:
                acc_id = int(acc_id)
                acc = Account.query.get(acc_id)
                if acc and not (current_user.is_admin or acc.user_id in (None, current_user.id)):
                    return jsonify({'error':'Keine Berechtigung für Konto'}),403
                r.account_id = acc_id
            except Exception:
                return jsonify({'error':'Ungültiges Konto'}),400
    db.session.add(AuditLog(actor_id=current_user.id, action='recurring_update', target_type='recurring', target_id=str(r.id)))
    db.session.commit()
    return jsonify({'status':'ok'})

@bp.route('/api/recurring/<int:rid>', methods=['DELETE'])
@login_required
def delete_recurring(rid):
    r = RecurringTransaction.query.get_or_404(rid)
    if r.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error':'Unauthorized'}),403
    db.session.add(AuditLog(actor_id=current_user.id, action='recurring_delete', target_type='recurring', target_id=str(r.id)))
    db.session.delete(r)
    db.session.commit()
    return jsonify({'status':'deleted'})

# ---------------- Budgets ------------------------
@bp.route('/api/budgets')
@login_required
def budgets():
    """Budgetübersicht. Admins sehen aggregiert alle oder via user_id Eingrenzung."""
    today = date.today()
    month_start = date(today.year, today.month, 1)
    next_month = date(today.year + (1 if today.month==12 else 0), 1 if today.month==12 else today.month+1, 1)
    user_id_param = request.args.get('user_id', type=int) if current_user.is_admin else None

    cat_query = db.session.query(Category)
    if current_user.is_admin:
        if user_id_param:
            cat_query = cat_query.filter(or_(Category.user_id==user_id_param, Category.user_id.is_(None)))
    else:
        cat_query = cat_query.filter(or_(Category.user_id==current_user.id, Category.user_id.is_(None)))
    rows = cat_query.all()
    spent_map = {c.id:0.0 for c in rows}

    exp_q = Expense.query.filter(Expense.date>=month_start, Expense.date<next_month)
    if current_user.is_admin:
        if user_id_param:
            exp_q = exp_q.filter(Expense.user_id==user_id_param)
    else:
        exp_q = exp_q.filter(Expense.user_id==current_user.id)
    for e in exp_q:
        if e.category_id in spent_map and e.kind=='expense':
            spent_map[e.category_id] += e.amount
    out=[]
    for c in rows:
        budget = c.monthly_budget or None
        spent = spent_map.get(c.id,0.0)
        pct = (spent / budget * 100) if (budget and budget>0) else None
        out.append({
            'id': c.id,
            'name': c.name,
            'color': c.color,
            'budget': budget,
            'spent': spent,
            'percent': pct,
            'category_type': c.category_type or 'expense'
        })
    return jsonify({'categories': out, 'is_admin': current_user.is_admin, 'filtered_user_id': user_id_param})

# ---------------- Export -------------------------
@bp.route('/api/export.csv')
@login_required
def export_csv():
    kind = request.args.get('kind')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    q = Expense.query
    if current_user.is_admin:
        user_id_param = request.args.get('user_id', type=int)
        if user_id_param:
            q = q.filter(Expense.user_id==user_id_param)
    else:
        q = q.filter(Expense.user_id==current_user.id)
    if kind in ('income','expense'):
        q = q.filter(Expense.kind==kind)
    if year:
        q = q.filter(func.extract('year', Expense.date)==year)
    if month:
        q = q.filter(func.extract('month', Expense.date)==month)
    q = q.order_by(Expense.date.asc())
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Datum','Art','Kategorie','Betrag','Beschreibung','UserID'])
    for e in q.all():
        val = e.amount if e.kind=='income' else -e.amount
        writer.writerow([e.date.isoformat(), e.kind, e.category, f"{val:.2f}", e.description, e.user_id])
    csv_data = output.getvalue()
    return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=finanzen_export.csv'})

# ---------------- Overview / Dashboard Metrics -----------------
@bp.route('/api/accounts/overview')
@login_required
def accounts_overview():
    """Liefert aggregierte Kennzahlen für neues Dashboard."""
    # Accounts Sichtbarkeit wie list_accounts
    acc_q = Account.query
    if not current_user.is_admin:
        acc_q = acc_q.filter((Account.user_id==current_user.id) | (Account.user_id.is_(None)))
    accounts = acc_q.all()
    total_balance = sum(a.balance for a in accounts)
    today = date.today()
    month_start = date(today.year, today.month, 1)
    exp_q = Expense.query.filter(Expense.date>=month_start, Expense.date<=today)
    if not current_user.is_admin:
        exp_q = exp_q.filter(Expense.user_id==current_user.id)
    incomes = 0.0
    expenses_sum = 0.0
    per_account = {a.id:{'id':a.id,'name':a.name,'balance':a.balance,'income':0.0,'expense':0.0} for a in accounts}
    for e in exp_q:
        if e.kind=='income':
            incomes += e.amount
            if e.account_id in per_account:
                per_account[e.account_id]['income'] += e.amount
        elif e.kind=='expense':
            expenses_sum += e.amount
            if e.account_id in per_account:
                per_account[e.account_id]['expense'] += e.amount
    net = incomes - expenses_sum
    # Top Kategorien (monat) expenses only
    cat_rows = db.session.query(Expense.category, func.sum(Expense.amount))\
        .filter(Expense.kind=='expense', Expense.date>=month_start, Expense.date<=today)
    if not current_user.is_admin:
        cat_rows = cat_rows.filter(Expense.user_id==current_user.id)
    cat_rows = cat_rows.group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).limit(5).all()
    top_categories = [{'category':c,'spent':float(v or 0)} for c,v in cat_rows]
    return jsonify({
        'totalBalance': total_balance,
        'monthIncome': incomes,
        'monthExpense': expenses_sum,
        'monthNet': net,
        'accounts': list(per_account.values()),
        'topCategories': top_categories,
        'currency': CURRENCY_SYMBOL
    })

# ---------------- Cashflow (Netto Flüsse je Tag) -----------------
@bp.route('/api/cashflow')
@login_required
def cashflow():
    days = max(1, min(180, request.args.get('days', default=90, type=int)))
    today = date.today()
    from datetime import timedelta
    start = today - timedelta(days=days-1)
    # Sichtbare Accounts
    acc_q = Account.query
    if not current_user.is_admin:
        acc_q = acc_q.filter((Account.user_id==current_user.id) | (Account.user_id.is_(None)))
    accounts = acc_q.all()
    acc_ids = [a.id for a in accounts]
    acc_index = {a.id: a for a in accounts}
    # Init daily map
    daily = {a.id:{} for a in accounts}
    # Expenses/Incomes als Flüsse
    flow_q = Expense.query.filter(Expense.date>=start, Expense.date<=today, Expense.account_id.in_(acc_ids))
    if not current_user.is_admin:
        flow_q = flow_q.filter(Expense.user_id==current_user.id)
    for e in flow_q:
        dkey = e.date.isoformat()
        delta = e.amount if e.kind=='income' else -e.amount
        daily[e.account_id][dkey] = daily[e.account_id].get(dkey, 0.0) + delta
    # Transfers
    tx_q = AccountTransaction.query.filter(AccountTransaction.created_at>=start)
    if not current_user.is_admin:
        # Eingeschränkt: nur Transfers, die sichtbar beteiligte Accounts betreffen
        tx_q = tx_q.filter(or_(AccountTransaction.from_account_id.in_(acc_ids), AccountTransaction.to_account_id.in_(acc_ids)))
    for tx in tx_q:
        day_key = tx.created_at.date().isoformat()
        if tx.from_account_id in acc_index:
            daily[tx.from_account_id][day_key] = daily[tx.from_account_id].get(day_key,0.0) - tx.amount
        if tx.to_account_id in acc_index:
            daily[tx.to_account_id][day_key] = daily[tx.to_account_id].get(day_key,0.0) + tx.amount
    # Build response with ordered days
    day_list = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    series = []
    for a in accounts:
        cum = 0.0
        points = []
        for dkey in day_list:
            cum += daily[a.id].get(dkey, 0.0)
            points.append({'day':dkey,'flow':daily[a.id].get(dkey,0.0),'cumulative':cum})
        series.append({'accountId': a.id, 'name': a.name, 'points': points, 'currentBalance': a.balance})
    return jsonify({'days': day_list, 'series': series, 'currency': CURRENCY_SYMBOL})

# ---------------- Accounts & Transfers -----------------
@bp.route('/api/accounts', methods=['GET'])
@login_required
def list_accounts():
    q = Account.query
    # Für Familie: alle shared (user_id is null) + eigene + (falls Admin) alle
    if current_user.is_admin:
        pass
    else:
        q = q.filter((Account.user_id==current_user.id) | (Account.user_id.is_(None)))
    rows = q.order_by(Account.name.asc()).all()
    return jsonify([
        {'id':a.id,'name':a.name,'balance':a.balance,'ownerId':a.user_id} for a in rows
    ])

@bp.route('/api/accounts', methods=['POST'])
@login_required
def create_account():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error':'Name erforderlich'}),400
    if Account.query.filter_by(name=name).first():
        return jsonify({'error':'Name existiert'}),400
    a = Account(name=name[:80], balance=0.0, user_id=current_user.id if not current_user.is_admin else data.get('ownerId'))
    db.session.add(a)
    db.session.commit()
    return jsonify({'id':a.id})

@bp.route('/api/accounts/transfer', methods=['POST'])
@login_required
def transfer_between_accounts():
    data = request.get_json() or {}
    try:
        from_id = int(data.get('from'))
        to_id = int(data.get('to'))
        amount = float(data.get('amount'))
    except Exception:
        return jsonify({'error':'Ungültige Daten'}),400
    if amount<=0:
        return jsonify({'error':'Betrag > 0 nötig'}),400
    if from_id == to_id:
        return jsonify({'error':'Gleiche Konten'}),400
    fa = Account.query.get_or_404(from_id)
    ta = Account.query.get_or_404(to_id)
    # Berechtigungen
    def can(acc):
        return current_user.is_admin or acc.user_id in (None, current_user.id)
    if not (can(fa) and can(ta)):
        return jsonify({'error':'Unauthorized'}),403
    if fa.balance < amount and not fa.allow_negative:
        return jsonify({'error':'Nicht genügend Guthaben'}),400
    fa.balance -= amount
    ta.balance += amount
    tx = AccountTransaction(from_account_id=fa.id, to_account_id=ta.id, amount=amount, description=(data.get('description') or '')[:200], actor_id=current_user.id)
    db.session.add(tx)
    # Audit
    db.session.add(AuditLog(actor_id=current_user.id, action='account_transfer', target_type='account', target_id=f'{fa.id}->{ta.id}', details=f'amount={amount}'))
    db.session.commit()
    _snapshot_accounts([fa.id, ta.id])
    return jsonify({'status':'ok','tx_id':tx.id,'from_balance':fa.balance,'to_balance':ta.balance})

def _validate_amount(amount: float):
    if amount <= 0:
        return 'Betrag > 0 nötig'
    if amount > MAX_TRANSACTION_AMOUNT:
        return f'Betrag überschreitet Limit ({MAX_TRANSACTION_AMOUNT})'
    return None

@bp.route('/api/projection')   # vorher: /finance/api/projection -> führte zu /finance/finance/api/projection
@login_required
def projection():
    from datetime import timedelta
    today = date.today()
    horizon_days = int(request.args.get('days', 30))
    end = today + timedelta(days=horizon_days)
    recs = RecurringTransaction.query.filter_by(user_id=current_user.id, active=True).all()
    # Simple monatlicher Faktor
    def monthly_equiv(r):
        if r.frequency=='weekly': return r.amount * (52/12)
        if r.frequency=='yearly': return r.amount / 12
        return r.amount
    monthly_net = sum((monthly_equiv(r) if r.kind=='income' else -monthly_equiv(r)) for r in recs)
    projected_period = monthly_net / 30 * horizon_days
    return jsonify({
        'horizon_days': horizon_days,
        'monthly_recurring_net': monthly_net,
        'projected_net_next_period': projected_period
    })

def _snapshot_accounts(account_ids):
    if not account_ids:
        return
    today = date.today()
    for aid in filter(None, set(account_ids)):
        acc = Account.query.get(aid)
        if not acc:
            continue
        snap = AccountBalanceSnapshot.query.filter_by(account_id=aid, day=today).first()
        if not snap:
            db.session.add(AccountBalanceSnapshot(account_id=aid, day=today, balance=acc.balance))
        else:
            snap.balance = acc.balance
    db.session.commit()
