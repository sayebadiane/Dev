from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SencleanMission(models.Model):
    _name = 'senclean.mission'
    _description = 'Mission SenClean'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Référence',
        readonly=True,
        default=lambda self: _('Nouveau'),
        copy=False,
    )

    # Parties prenantes
    client_id = fields.Many2one(
        'res.partner', string='Client', required=True, tracking=True
    )
    provider_id = fields.Many2one(
        'senclean.provider', string='Prestataire', required=True, tracking=True
    )
    category_id = fields.Many2one(
        'senclean.service.category', string='Catégorie de service', required=True
    )

    # Planification
    service_type = fields.Selection([
        ('ponctuel', 'Ponctuel'),
        ('recurrent', 'Récurrent'),
    ], string='Type de service', default='ponctuel', required=True)
    date_start = fields.Datetime(string='Date et heure de début', required=True, tracking=True)
    date_end = fields.Datetime(string='Date et heure de fin')
    duration_hours = fields.Float(
        string='Durée (heures)',
        compute='_compute_duration',
        store=True,
    )
    address = fields.Char(string='Adresse d\'intervention', required=True)
    city = fields.Char(string='Ville', default='Dakar')

    # Tarification
    rate_type = fields.Selection(
        related='provider_id.rate_type', string='Mode tarification', store=True
    )
    hourly_rate = fields.Float(string='Tarif horaire (FCFA)', digits=(10, 0))
    amount_total = fields.Float(
        string='Montant total (FCFA)',
        compute='_compute_amount',
        store=True,
        digits=(10, 0),
    )
    commission_rate = fields.Float(string='Taux commission (%)', default=12.0)
    commission_amount = fields.Float(
        string='Commission SenClean (FCFA)',
        compute='_compute_amount',
        store=True,
        digits=(10, 0),
    )
    provider_amount = fields.Float(
        string='Montant prestataire (FCFA)',
        compute='_compute_amount',
        store=True,
        digits=(10, 0),
    )

    # Paiement
    payment_frequency = fields.Selection([
        ('immediate', 'Paiement immédiat'),
        ('monthly', 'Fin de mois'),
    ], string='Fréquence de paiement', default='immediate', required=True, tracking=True)
    monthly_billing_id = fields.Many2one(
        'senclean.monthly.billing',
        string='Facturation mensuelle',
        ondelete='set null',
        readonly=True,
    )
    payment_method = fields.Selection([
        ('wave', 'Wave'),
        ('orange_money', 'Orange Money'),
        ('free_money', 'Free Money'),
        ('cash', 'Espèces'),
    ], string='Moyen de paiement', tracking=True)
    payment_state = fields.Selection([
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('refunded', 'Remboursé'),
    ], string='Statut paiement', default='pending', tracking=True)
    payment_ref = fields.Char(string='Référence paiement')
    payment_date = fields.Datetime(string='Date de paiement')

    # Statut mission
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string='Statut', default='draft', required=True, tracking=True)

    # Instructions et notes
    instructions = fields.Text(string='Instructions pour le prestataire')
    client_note = fields.Text(string='Notes post-mission (client)')
    provider_note = fields.Text(string='Notes post-mission (prestataire)')

    # Évaluation
    rating = fields.Integer(string='Note client (1-5)', default=0)
    rating_comment = fields.Text(string='Commentaire client')

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = rec.date_end - rec.date_start
                rec.duration_hours = delta.total_seconds() / 3600
            else:
                rec.duration_hours = 0.0

    @api.depends('duration_hours', 'hourly_rate', 'commission_rate', 'rate_type')
    def _compute_amount(self):
        for rec in self:
            if rec.rate_type == 'monthly':
                # Pour les forfaits mensuels, le montant de la mission individuelle
                # n'est qu'indicatif — la facturation réelle se fait via la facturation mensuelle
                total = 0.0
            else:
                total = rec.duration_hours * rec.hourly_rate
            commission = total * (rec.commission_rate / 100)
            rec.amount_total = total
            rec.commission_amount = commission
            rec.provider_amount = total - commission

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('senclean.mission') or _('Nouveau')
        return super().create(vals_list)

    @api.onchange('provider_id')
    def _onchange_provider(self):
        if self.provider_id:
            self.hourly_rate = self.provider_id.hourly_rate
            if self.provider_id.rate_type == 'monthly':
                self.payment_frequency = 'monthly'
                self.service_type = 'recurrent'
            else:
                self.payment_frequency = 'immediate'

    # --- Actions workflow ---

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Seule une mission en brouillon peut être confirmée."))
            rec.state = 'confirmed'
            rec.message_post(body=_("Mission confirmée."))

    def action_start(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("La mission doit être confirmée avant de démarrer."))
            rec.state = 'in_progress'
            rec.message_post(body=_("Mission démarrée."))

    def action_done(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_("La mission doit être en cours pour être terminée."))
            rec.state = 'done'
            rec.message_post(body=_("Mission terminée avec succès."))

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("Une mission terminée ne peut pas être annulée."))
            rec.state = 'cancelled'
            rec.message_post(body=_("Mission annulée."))

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Seule une mission annulée peut être remise en brouillon."))
            rec.state = 'draft'
