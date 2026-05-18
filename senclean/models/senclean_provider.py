from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SencleanProvider(models.Model):
    _name = 'senclean.provider'
    _description = 'Prestataire SenClean'
    _inherit = ['mail.activity.mixin', 'rating.mixin']
    _order = 'name'
    _rec_name = 'name'

    # Informations personnelles
    name = fields.Char(string='Nom complet', required=True, tracking=True)
    photo = fields.Image(string='Photo', max_width=512, max_height=512)
    phone = fields.Char(string='Téléphone', required=True, tracking=True)
    email = fields.Char(string='Email')
    address = fields.Char(string='Adresse')
    city = fields.Char(string='Ville', default='Dakar')
    partner_id = fields.Many2one('res.partner', string='Contact Odoo', ondelete='set null')

    # Identité et vérification
    id_type = fields.Selection([
        ('cni', "Carte Nationale d'Identité"),
        ('passport', 'Passeport'),
        ('permis', 'Permis de conduire'),
    ], string="Type de pièce d'identité", default='cni')
    id_number = fields.Char(string="Numéro de pièce d'identité")
    id_document = fields.Binary(string="Document identité (scan)")
    id_document_name = fields.Char()

    # Profil professionnel
    category_ids = fields.Many2many(
        'senclean.service.category',
        'senclean_provider_category_rel',
        'provider_id', 'category_id',
        string='Catégories de services',
        required=True,
    )
    experience_years = fields.Integer(string='Années d\'expérience', default=0)
    bio = fields.Text(string='Présentation / Bio')
    availability = fields.Text(string='Disponibilités')

    # Tarification
    rate_type = fields.Selection([
        ('hourly', 'À l\'heure'),
        ('monthly', 'Forfait mensuel'),
    ], string='Mode de tarification', default='hourly', required=True, tracking=True)
    hourly_rate = fields.Float(
        string='Tarif horaire (FCFA)', digits=(10, 0),
        help="Applicable si le mode de tarification est 'À l\'heure'",
    )
    monthly_rate = fields.Float(
        string='Forfait mensuel (FCFA)', digits=(10, 0),
        help="Montant fixe payé en fin de mois, quel que soit le nombre de jours travaillés",
    )

    # Géolocalisation
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    intervention_radius_km = fields.Integer(string='Rayon d\'intervention (km)', default=5)

    # Statut et workflow
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('verified', 'Identité vérifiée'),
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
        ('rejected', 'Refusé'),
    ], string='Statut', default='draft', required=True, tracking=True)

    # Badge premium
    is_premium = fields.Boolean(string='Prestataire Premium', default=False, tracking=True)
    is_certified = fields.Boolean(string='Certifié SenClean', default=False, tracking=True)

    # Statistiques
    mission_count = fields.Integer(
        string='Nb missions',
        compute='_compute_mission_stats',
        store=True,
    )
    mission_done_count = fields.Integer(
        string='Missions terminées',
        compute='_compute_mission_stats',
        store=True,
    )
    rating_avg = fields.Float(
        string='Note moyenne',
        compute='_compute_rating_avg',
        store=True,
        digits=(3, 2),
    )

    # Dates
    registration_date = fields.Date(
        string='Date d\'inscription',
        default=fields.Date.today,
    )
    validation_date = fields.Date(string='Date de validation')
    validated_by = fields.Many2one('res.users', string='Validé par', readonly=True)

    # Notes admin
    admin_note = fields.Text(string='Notes internes admin')

    @api.depends('mission_ids', 'mission_ids.state')
    def _compute_mission_stats(self):
        for rec in self:
            missions = rec.mission_ids
            rec.mission_count = len(missions)
            rec.mission_done_count = len(missions.filtered(lambda m: m.state == 'done'))

    @api.depends('rating_ids.rating')
    def _compute_rating_avg(self):
        for rec in self:
            ratings = rec.rating_ids.filtered(lambda r: r.rating > 0)
            rec.rating_avg = sum(ratings.mapped('rating')) / len(ratings) if ratings else 0.0

    mission_ids = fields.One2many(
        'senclean.mission', 'provider_id', string='Missions'
    )

    # --- Actions workflow ---

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Seul un prestataire en brouillon peut être soumis."))
            if not rec.category_ids:
                raise UserError(_("Veuillez sélectionner au moins une catégorie de service."))
            rec.state = 'submitted'
            rec.message_post(body=_("Dossier soumis pour vérification."))

    def action_verify_identity(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("L'identité ne peut être vérifiée que pour un dossier soumis."))
            rec.state = 'verified'
            rec.message_post(body=_("Identité vérifiée par l'administrateur."))

    def action_activate(self):
        for rec in self:
            if rec.state not in ('verified', 'suspended'):
                raise UserError(_("Le prestataire doit être vérifié ou suspendu pour être activé."))
            rec.state = 'active'
            rec.validation_date = fields.Date.today()
            rec.validated_by = self.env.user
            rec._create_or_update_portal_user()
            rec.message_post(body=_("Profil activé — prestataire visible sur la plateforme."))

    def _create_or_update_portal_user(self):
        """Crée ou réactive le compte portail du prestataire lors de l'activation."""
        self.ensure_one()
        if not self.email:
            self.message_post(body=_(
                "Aucun email renseigné — le compte portail n'a pas pu être créé. "
                "Ajoutez un email et relancez l'activation."
            ))
            return

        Partner = self.env['res.partner'].sudo()
        User = self.env['res.users'].sudo()
        portal_group = self.env.ref('base.group_portal')

        # 1. Créer le res.partner s'il n'existe pas encore
        if not self.partner_id:
            partner = Partner.create({
                'name': self.name,
                'phone': self.phone,
                'email': self.email,
                'street': self.address,
                'city': self.city or 'Dakar',
            })
            self.partner_id = partner
        else:
            partner = self.partner_id
            if not partner.email:
                partner.write({'email': self.email})

        # 2. Chercher un compte utilisateur existant pour ce partner
        user = User.search([
            ('partner_id', '=', partner.id),
            ('active', 'in', [True, False]),
        ], limit=1)

        group_public = self.env.ref('base.group_public')

        if user:
            # Réactiver si archivé + s'assurer qu'il est dans le groupe portail
            user.write({
                'active': True,
                'group_ids': [(4, portal_group.id), (3, group_public.id)],
            })
            # Préparer le lien de connexion
            partner.signup_prepare()
            msg = _("Compte portail réactivé pour %s (%s).") % (self.name, self.email)
        else:
            # Vérifier que le login n'est pas déjà pris par un autre user
            existing = User.search([('login', '=', self.email)], limit=1)
            if existing:
                self.message_post(body=_(
                    "L'adresse email %s est déjà utilisée par un autre compte. "
                    "Le compte portail n'a pas pu être créé automatiquement."
                ) % self.email)
                return

            # Créer via le template portail (méthode officielle Odoo 19)
            from odoo.tools.mail import email_normalize
            User.with_context(no_reset_password=True)._create_user_from_template({
                'email': email_normalize(self.email),
                'login': email_normalize(self.email),
                'partner_id': partner.id,
                'company_id': self.env.company.id,
                'company_ids': [(6, 0, self.env.company.ids)],
            })
            msg = _("Compte portail créé — le prestataire peut se connecter avec l'adresse %s.") % self.email

        self.message_post(body=msg)

    def action_suspend(self):
        for rec in self:
            if rec.state != 'active':
                raise UserError(_("Seul un prestataire actif peut être suspendu."))
            rec.state = 'suspended'
            rec.message_post(body=_("Profil suspendu."))

    def action_reject(self):
        for rec in self:
            if rec.state in ('active', 'rejected'):
                raise UserError(_("Ce prestataire ne peut pas être refusé dans son état actuel."))
            rec.state = 'rejected'
            rec.message_post(body=_("Dossier refusé."))

    def action_view_missions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Missions de %s') % self.name,
            'res_model': 'senclean.mission',
            'view_mode': 'list,form',
            'domain': [('provider_id', '=', self.id)],
            'context': {'default_provider_id': self.id},
        }

    def action_view_missions_done(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Missions terminées de %s') % self.name,
            'res_model': 'senclean.mission',
            'view_mode': 'list,form',
            'domain': [('provider_id', '=', self.id), ('state', '=', 'done')],
            'context': {'default_provider_id': self.id},
        }

    def action_reset_draft(self):
        for rec in self:
            if rec.state not in ('rejected', 'suspended'):
                raise UserError(_("Seul un dossier refusé ou suspendu peut être remis en brouillon."))
            rec.state = 'draft'
