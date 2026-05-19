from odoo import http, _
from odoo.http import request
from odoo.tools.mail import email_normalize
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


# Mapping ti-* icons → Font Awesome 4/5 (disponible dans Odoo portal)
ICON_MAP = {
    'ti-home': 'fa-home',
    'ti-heart': 'fa-heart',
    'ti-baby-carriage': 'fa-child',
    'ti-shirt': 'fa-magic',
    'ti-building': 'fa-building',
    'ti-sparkles': 'fa-star',
    'ti-broom': 'fa-tint',
    'ti-tool': 'fa-wrench',
}

# Couleurs des icônes de catégories (bg, color) par séquence
CAT_COLORS = [
    ('#E8F5E9', '#2E7D52'),   # vert
    ('#E3F2FD', '#1565C0'),   # bleu
    ('#FFF3E0', '#E65100'),   # orange
    ('#FCE4EC', '#C62828'),   # rose
    ('#EDE7F6', '#6A1B9A'),   # violet
    ('#E0F7FA', '#00695C'),   # teal
    ('#F3E5F5', '#7B1FA2'),   # pourpre
    ('#E8EAF6', '#283593'),   # indigo
]

# Couleurs des avatars prestataires (cycle)
AVATAR_COLORS = [
    '#1A5C3A', '#1565C0', '#E65100', '#C62828',
    '#6A1B9A', '#00695C', '#283593', '#37474F',
]


class SencleanPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'mission_count' in counters:
            values['mission_count'] = request.env['senclean.mission'].sudo().search_count(
                [('client_id', '=', partner.id)]
            )

        if 'provider_count' in counters:
            values['provider_count'] = request.env['senclean.provider'].sudo().search_count(
                [('partner_id', '=', partner.id)]
            )

        return values

    # ------------------------------------------------------------------
    # /my  et  /my/home  → Page d'accueil SenClean
    # ------------------------------------------------------------------

    @http.route(['/my', '/my/home'], type='http', auth='public', website=True)
    def home(self, **kw):
        """Page d'accueil — visiteur non connecté ou dashboard connecté."""
        is_public = request.env.user._is_public()

        values = self._prepare_portal_layout_values()
        values['page_name'] = 'home'
        values['is_public'] = is_public

        if is_public:
            # ── État VISITEUR : catégories + un prestataire en aperçu ──
            values.update(self._build_guest_home_values())
            return request.render('senclean.portal_home', values)

        partner = request.env.user.partner_id
        first_name = (partner.name or '').split()[0] if partner.name else 'vous'

        # ── Détecter si l'utilisateur est un prestataire ──────────────
        provider = request.env['senclean.provider'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )

        values['first_name'] = first_name

        if provider:
            # ── Dashboard PRESTATAIRE ──────────────────────────────────
            Mission = request.env['senclean.mission'].sudo()

            upcoming = Mission.search([
                ('provider_id', '=', provider.id),
                ('state', 'in', ['confirmed', 'in_progress']),
            ], order='date_start asc', limit=5)

            recent_done = Mission.search([
                ('provider_id', '=', provider.id),
                ('state', '=', 'done'),
            ], order='date_start desc', limit=3)

            unpaid_count = Mission.search_count([
                ('provider_id', '=', provider.id),
                ('payment_state', '=', 'pending'),
                ('state', '=', 'done'),
            ])

            parts = (provider.name or '').split()
            initials = ''.join(x[0].upper() for x in parts[:2]) if parts else '?'

            values.update({
                'is_provider': True,
                'provider': provider,
                'provider_initials': initials,
                'provider_avatar_color': AVATAR_COLORS[0],
                'upcoming_missions': upcoming,
                'recent_done': recent_done,
                'unpaid_count': unpaid_count,
            })
        else:
            # ── Dashboard CLIENT ────────────────────────────────────────
            categories_raw = request.env['senclean.service.category'].sudo().search(
                [('active', '=', True)], order='sequence, name'
            )
            categories = []
            for idx, cat in enumerate(categories_raw):
                color_pair = CAT_COLORS[idx % len(CAT_COLORS)]
                categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'bg_color': color_pair[0],
                    'icon_color': color_pair[1],
                    'fa_icon': ICON_MAP.get(cat.icon or '', 'fa-circle'),
                })

            providers_raw = request.env['senclean.provider'].sudo().search(
                [('state', '=', 'active')], order='rating_avg desc, name', limit=6
            )
            providers = []
            for idx, p in enumerate(providers_raw):
                parts = (p.name or '').split()
                initials = ''.join(x[0].upper() for x in parts[:2]) if parts else '?'
                main_cat = p.category_ids[:1].name if p.category_ids else ''
                rate_label = (
                    '{:,.0f} F/mois'.format(p.monthly_rate)
                    if p.rate_type == 'monthly'
                    else '{:,.0f} F/h'.format(p.hourly_rate)
                )
                providers.append({
                    'id': p.id,
                    'name': p.name,
                    'initials': initials,
                    'avatar_color': AVATAR_COLORS[idx % len(AVATAR_COLORS)],
                    'main_cat': main_cat,
                    'rate_label': rate_label,
                    'rating_avg': p.rating_avg,
                    'is_certified': p.is_certified,
                    'state': p.state,
                    'provider_id': p.id,
                })

            values.update({
                'is_provider': False,
                'categories': categories,
                'providers': providers,
            })

        return request.render('senclean.portal_home', values)

    def _build_guest_home_values(self):
        """Données pour la page d'accueil visiteur non connecté."""
        categories_raw = request.env['senclean.service.category'].sudo().search(
            [('active', '=', True)], order='sequence, name'
        )
        categories = []
        for idx, cat in enumerate(categories_raw):
            color_pair = CAT_COLORS[idx % len(CAT_COLORS)]
            categories.append({
                'id': cat.id,
                'name': cat.name,
                'bg_color': color_pair[0],
                'icon_color': color_pair[1],
                'fa_icon': ICON_MAP.get(cat.icon or '', 'fa-circle'),
            })

        teaser_raw = request.env['senclean.provider'].sudo().search(
            [('state', '=', 'active')], order='rating_avg desc', limit=1
        )
        teaser_providers = []
        for idx, p in enumerate(teaser_raw):
            parts = (p.name or '').split()
            initials = ''.join(x[0].upper() for x in parts[:2]) if parts else '?'
            main_cat = p.category_ids[:1].name if p.category_ids else ''
            rate_label = (
                '{:,.0f} F/mois'.format(p.monthly_rate)
                if p.rate_type == 'monthly'
                else '{:,.0f} F/h'.format(p.hourly_rate)
            )
            teaser_providers.append({
                'name': p.name,
                'initials': initials,
                'avatar_color': AVATAR_COLORS[idx % len(AVATAR_COLORS)],
                'main_cat': main_cat,
                'rate_label': rate_label,
                'rating_avg': p.rating_avg,
            })

        return {
            'is_provider': False,
            'categories': categories,
            'teaser_providers': teaser_providers,
        }

    # ------------------------------------------------------------------
    # /my/missions — liste des missions du client connecté
    # ------------------------------------------------------------------

    @http.route(['/my/missions', '/my/missions/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_missions(self, page=1, filter_state='all', **kw):
        partner = request.env.user.partner_id
        Mission = request.env['senclean.mission'].sudo()

        base_domain = [('client_id', '=', partner.id)]

        STATE_FILTERS = {
            'all':        {'label': 'Toutes',     'domain': []},
            'confirmed':  {'label': 'Confirmées', 'domain': [('state', '=', 'confirmed')]},
            'in_progress':{'label': 'En cours',   'domain': [('state', '=', 'in_progress')]},
            'done':       {'label': 'Terminées',  'domain': [('state', '=', 'done')]},
            'cancelled':  {'label': 'Annulées',   'domain': [('state', '=', 'cancelled')]},
        }
        active_filter = filter_state if filter_state in STATE_FILTERS else 'all'
        domain = base_domain + STATE_FILTERS[active_filter]['domain']

        total = Mission.search_count(domain)
        pager = portal_pager(
            url='/my/missions',
            url_args={'filter_state': active_filter},
            total=total, page=page, step=10,
        )
        missions_raw = Mission.search(domain, order='date_start desc',
                                      limit=10, offset=pager['offset'])

        # Construire les données enrichies pour chaque mission
        missions = []
        for m in missions_raw:
            parts = (m.provider_id.name or '').split()
            initials = ''.join(x[0].upper() for x in parts[:2]) if parts else '?'
            prov_idx = m.provider_id.id % len(AVATAR_COLORS)
            rate_label = ''
            if m.rate_type == 'monthly':
                rate_label = 'Forfait mensuel'
            elif m.hourly_rate:
                rate_label = '{:,.0f} FCFA/h'.format(m.hourly_rate)

            missions.append({
                'id': m.id,
                'name': m.name,
                'state': m.state,
                'payment_state': m.payment_state,
                'date_start': m.date_start,
                'provider_name': m.provider_id.name or '',
                'provider_initials': initials,
                'provider_avatar_color': AVATAR_COLORS[prov_idx],
                'provider_id': m.provider_id.id,
                'category': m.category_id.name or '',
                'address': m.address or '',
                'city': m.city or '',
                'rate_label': rate_label,
                'amount_total': m.amount_total,
                'rate_type': m.rate_type,
                'is_certified': m.provider_id.is_certified,
            })

        # Compteurs par statut pour les badges
        counts = {
            'all':         Mission.search_count(base_domain),
            'confirmed':   Mission.search_count(base_domain + [('state', '=', 'confirmed')]),
            'in_progress': Mission.search_count(base_domain + [('state', '=', 'in_progress')]),
            'done':        Mission.search_count(base_domain + [('state', '=', 'done')]),
            'cancelled':   Mission.search_count(base_domain + [('state', '=', 'cancelled')]),
        }

        values = self._prepare_portal_layout_values()
        values.update({
            'missions': missions,
            'state_filters': STATE_FILTERS,
            'active_filter': active_filter,
            'counts': counts,
            'page_name': 'mission',
            'pager': pager,
        })
        return request.render('senclean.portal_my_missions', values)

    @http.route('/my/missions/<int:mission_id>', type='http',
                auth='user', website=True)
    def portal_mission_detail(self, mission_id, **kw):
        partner = request.env.user.partner_id
        mission = request.env['senclean.mission'].sudo().browse(mission_id)
        if not mission.exists() or mission.client_id != partner:
            return request.not_found()

        values = self._prepare_portal_layout_values()
        values.update({
            'mission': mission,
            'page_name': 'mission',
        })
        return request.render('senclean.portal_mission_detail', values)

    # ------------------------------------------------------------------
    # /my/provider/missions — missions du prestataire connecté
    # ------------------------------------------------------------------

    @http.route(['/my/provider/missions', '/my/provider/missions/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_provider_missions(self, page=1, sortby='date', **kw):
        partner = request.env.user.partner_id
        provider = request.env['senclean.provider'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )
        if not provider:
            return request.redirect('/my')

        Mission = request.env['senclean.mission'].sudo()
        sortings = {
            'date': {'label': _('Date'), 'order': 'date_start desc'},
            'state': {'label': _('Statut'), 'order': 'state'},
        }
        order = sortings.get(sortby, sortings['date'])['order']
        domain = [('provider_id', '=', provider.id)]
        total = Mission.search_count(domain)

        pager = portal_pager(
            url='/my/provider/missions',
            url_args={'sortby': sortby},
            total=total, page=page, step=10,
        )
        missions = Mission.search(domain, order=order, limit=10, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'provider': provider,
            'missions': missions,
            'page_name': 'provider_missions',
            'pager': pager,
            'sortby': sortby,
            'searchbar_sortings': sortings,
        })
        return request.render('senclean.portal_provider_missions', values)

    @http.route('/my/provider/missions/<int:mission_id>',
                type='http', auth='user', website=True)
    def portal_provider_mission_detail(self, mission_id, **kw):
        partner = request.env.user.partner_id
        provider = request.env['senclean.provider'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )
        mission = request.env['senclean.mission'].sudo().browse(mission_id)
        if not provider or not mission.exists() or mission.provider_id != provider:
            return request.not_found()

        values = self._prepare_portal_layout_values()
        values.update({
            'mission': mission,
            'is_provider_view': True,
            'page_name': 'provider_missions',
        })
        return request.render('senclean.portal_mission_detail', values)

    # ------------------------------------------------------------------
    # /providers  — liste publique des prestataires (sans connexion)
    # ------------------------------------------------------------------

    @http.route(['/providers', '/providers/page/<int:page>'],
                type='http', auth='public', website=True)
    def portal_providers_list(self, page=1, category=None, city=None,
                               sortby='rating', search='', **kw):
        """Liste publique — accessible sans connexion."""
        Provider = request.env['senclean.provider'].sudo()
        Category = request.env['senclean.service.category'].sudo()

        domain = [('state', '=', 'active')]
        if category:
            domain += [('category_ids', 'in', [int(category)])]
        if city:
            domain += [('city', 'ilike', city)]
        if search:
            domain += [('name', 'ilike', search)]

        sortings = {
            'rating':  {'label': _('Meilleure note'),  'order': 'rating_avg desc'},
            'price':   {'label': _('Prix croissant'),   'order': 'hourly_rate asc'},
            'name':    {'label': _('Nom A→Z'),          'order': 'name asc'},
        }
        order = sortings.get(sortby, sortings['rating'])['order']

        total = Provider.search_count(domain)
        pager = portal_pager(
            url='/providers',
            url_args={'category': category, 'city': city,
                      'sortby': sortby, 'search': search},
            total=total, page=page, step=9,
        )
        providers_raw = Provider.search(domain, order=order,
                                         limit=9, offset=pager['offset'])

        providers = []
        for idx, p in enumerate(providers_raw):
            parts = (p.name or '').split()
            initials = ''.join(x[0].upper() for x in parts[:2]) if parts else '?'
            rate_label = (
                '{:,.0f} F/mois'.format(p.monthly_rate)
                if p.rate_type == 'monthly'
                else '{:,.0f} F/h'.format(p.hourly_rate)
            )
            providers.append({
                'id': p.id,
                'name': p.name,
                'initials': initials,
                'avatar_color': AVATAR_COLORS[idx % len(AVATAR_COLORS)],
                'main_cat': p.category_ids[:1].name if p.category_ids else '',
                'categories': p.category_ids.mapped('name'),
                'rate_label': rate_label,
                'rating_avg': p.rating_avg,
                'mission_done_count': p.mission_done_count,
                'is_certified': p.is_certified,
                'is_premium': p.is_premium,
                'city': p.city or '',
            })

        categories = Category.search([('active', '=', True)], order='sequence, name')

        selected_cat_id = int(category) if category else None
        selected_cat_name = ''
        if selected_cat_id:
            cat_rec = Category.browse(selected_cat_id)
            selected_cat_name = cat_rec.name if cat_rec.exists() else ''

        values = self._prepare_portal_layout_values()
        values.update({
            'providers': providers,
            'categories': categories,
            'pager': pager,
            'sortby': sortby,
            'searchbar_sortings': sortings,
            'search': search,
            'selected_category': selected_cat_id,
            'selected_category_name': selected_cat_name,
            'selected_city': city or '',
            'page_name': 'providers',
            'is_public': request.env.user._is_public(),
        })
        return request.render('senclean.portal_providers_list', values)

    # ------------------------------------------------------------------
    # /providers/<id> — profil public d'un prestataire (sans connexion)
    # ------------------------------------------------------------------

    @http.route('/providers/<int:provider_id>', type='http',
                auth='public', website=True)
    def portal_provider_detail(self, provider_id, **kw):
        provider = request.env['senclean.provider'].sudo().browse(provider_id)
        if not provider.exists() or provider.state != 'active':
            return request.not_found()

        values = self._prepare_portal_layout_values()
        values.update({
            'provider': provider,
            'page_name': 'providers',
            'is_public': request.env.user._is_public(),
        })
        return request.render('senclean.portal_provider_detail', values)

    # ------------------------------------------------------------------
    # /inscription — page d'inscription client (publique)
    # ------------------------------------------------------------------

    @http.route('/inscription', type='http', auth='public',
                website=True, methods=['GET', 'POST'])
    def portal_inscription(self, redirect=None, **kw):
        """Inscription d'un nouveau client SenClean."""
        # Si déjà connecté → redirection
        if not request.env.user._is_public():
            return request.redirect(redirect or '/my')

        error = {}
        values = {
            'redirect': redirect or '/my',
            'kw': kw,
            'error': error,
        }

        if request.httprequest.method == 'POST':
            name     = kw.get('name', '').strip()
            phone    = kw.get('phone', '').strip()
            email    = kw.get('email', '').strip()
            password = kw.get('password', '')
            confirm  = kw.get('confirm_password', '')
            address  = kw.get('address', '').strip()
            city     = kw.get('city', 'Dakar').strip()

            # Validation
            if not name:
                error['name'] = _("Le nom est obligatoire.")
            if not phone:
                error['phone'] = _("Le téléphone est obligatoire.")
            if not email or '@' not in email:
                error['email'] = _("Email invalide.")
            if not password or len(password) < 6:
                error['password'] = _("Le mot de passe doit faire au moins 6 caractères.")
            if password != confirm:
                error['confirm_password'] = _("Les mots de passe ne correspondent pas.")

            if not error:
                # Vérifier unicité du login
                existing_user = request.env['res.users'].sudo().search(
                    [('login', '=', email_normalize(email))], limit=1
                )
                if existing_user:
                    error['email'] = _("Cette adresse email est déjà utilisée.")

            if not error:
                # 1. Créer le partner
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'phone': phone,
                    'email': email_normalize(email),
                    'street': address,
                    'city': city,
                })

                # 2. Créer le compte portail
                portal_group = request.env.ref('base.group_portal')
                user = request.env['res.users'].sudo().with_context(
                    no_reset_password=True
                )._create_user_from_template({
                    'email': email_normalize(email),
                    'login': email_normalize(email),
                    'partner_id': partner.id,
                    'company_id': request.env.company.id,
                    'company_ids': [(6, 0, request.env.company.ids)],
                })
                user.sudo().write({
                    'password': password,
                    'group_ids': [(4, portal_group.id)],
                })

                # 3. Créer le profil client SenClean
                request.env['senclean.client'].sudo()._create_from_portal_signup(
                    name=name, phone=phone, email=email,
                    address=address, city=city, partner=partner
                )

                # 4. Connecter automatiquement l'utilisateur
                # Odoo 19 : authenticate(env, {'type':'password','login':...,'password':...})
                request.session.authenticate(
                    request.env,
                    {
                        'type': 'password',
                        'login': email_normalize(email),
                        'password': password,
                    }
                )

                return request.redirect(redirect or '/my')

        return request.render('senclean.portal_inscription', values)

    # ------------------------------------------------------------------
    # /my/book/<provider_id> — formulaire de réservation (auth requis)
    # ------------------------------------------------------------------

    @http.route('/my/book/<int:provider_id>', type='http',
                auth='public', website=True, methods=['GET', 'POST'])
    def portal_book_provider(self, provider_id, **kw):
        """Redirige vers inscription si non connecté."""
        if request.env.user._is_public():
            return request.redirect(
                '/inscription?redirect=/my/book/%d' % provider_id
            )
        partner = request.env.user.partner_id
        provider = request.env['senclean.provider'].sudo().browse(provider_id)
        if not provider.exists() or provider.state != 'active':
            return request.not_found()

        categories = provider.category_ids
        error = {}
        success = False

        if request.httprequest.method == 'POST':
            category_id = kw.get('category_id')
            date_start   = kw.get('date_start')
            address      = kw.get('address', '').strip()
            city         = kw.get('city', '').strip()
            instructions = kw.get('instructions', '').strip()

            # Validation
            if not category_id:
                error['category_id'] = _("Veuillez choisir une catégorie.")
            if not date_start:
                error['date_start'] = _("Veuillez choisir une date et heure.")
            if not address:
                error['address'] = _("Veuillez saisir l'adresse d'intervention.")

            if not error:
                from datetime import datetime as dt
                # datetime-local HTML envoie '2026-05-19T15:00', Odoo attend un objet datetime
                try:
                    date_start_dt = dt.strptime(date_start, '%Y-%m-%dT%H:%M')
                except ValueError:
                    date_start_dt = dt.strptime(date_start, '%Y-%m-%d %H:%M:%S')

                Mission = request.env['senclean.mission']
                mission = Mission.sudo().create({
                    'client_id':    partner.id,
                    'provider_id':  provider.id,
                    'category_id':  int(category_id),
                    'date_start':   date_start_dt,
                    'address':      address,
                    'city':         city or provider.city or 'Dakar',
                    'instructions': instructions,
                    'hourly_rate':  provider.hourly_rate,
                    'payment_frequency': (
                        'monthly' if provider.rate_type == 'monthly' else 'immediate'
                    ),
                    'service_type': (
                        'recurrent' if provider.rate_type == 'monthly' else 'ponctuel'
                    ),
                })
                return request.redirect(
                    '/my/missions/%d?booked=1' % mission.id
                )

        values = self._prepare_portal_layout_values()
        values.update({
            'provider': provider,
            'categories': categories,
            'error': error,
            'page_name': 'providers',
            'kw': kw,
        })
        return request.render('senclean.portal_book_provider', values)

    # ------------------------------------------------------------------
    # /my/provider — profil prestataire du compte connecté
    # ------------------------------------------------------------------

    @http.route('/my/provider', type='http', auth='user', website=True)
    def portal_my_provider(self, **kw):
        partner = request.env.user.partner_id
        provider = request.env['senclean.provider'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )
        if not provider:
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()
        values.update({
            'provider': provider,
            'page_name': 'provider',
        })
        return request.render('senclean.portal_my_provider', values)
