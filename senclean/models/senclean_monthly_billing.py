from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class SencleanMonthlyBilling(models.Model):
    _name = 'senclean.monthly.billing'
    _description = 'Facturation mensuelle SenClean'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'billing_month desc, name'

    name = fields.Char(
        string='Référence',
        readonly=True,
        default=lambda self: _('Nouveau'),
        copy=False,
    )
    client_id = fields.Many2one(
        'res.partner', string='Client', required=True, tracking=True
    )
    provider_id = fields.Many2one(
        'senclean.provider', string='Prestataire', required=True, tracking=True
    )
    billing_month = fields.Date(
        string='Mois de facturation', required=True, tracking=True,
        help="Sélectionner le 1er jour du mois concerné",
    )
    billing_month_display = fields.Char(
        string='Période',
        compute='_compute_billing_month_display',
        store=True,
    )

    # Missions du mois
    mission_ids = fields.One2many(
        'senclean.mission', 'monthly_billing_id', string='Missions du mois'
    )
    mission_count = fields.Integer(
        string='Nb de passages',
        compute='_compute_totals',
        store=True,
    )

    # Montants
    rate_type = fields.Selection(
        related='provider_id.rate_type', string='Mode tarification', store=True
    )
    monthly_rate = fields.Float(
        string='Forfait mensuel (FCFA)', digits=(10, 0),
        compute='_compute_totals', store=True,
    )
    amount_total = fields.Float(
        string='Montant total (FCFA)', digits=(10, 0),
        compute='_compute_totals', store=True,
    )
    commission_rate = fields.Float(string='Taux commission (%)', default=12.0)
    commission_amount = fields.Float(
        string='Commission SenClean (FCFA)', digits=(10, 0),
        compute='_compute_totals', store=True,
    )
    provider_amount = fields.Float(
        string='Montant prestataire (FCFA)', digits=(10, 0),
        compute='_compute_totals', store=True,
    )

    # Paiement
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

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('paid', 'Payée'),
        ('cancelled', 'Annulée'),
    ], string='Statut', default='draft', required=True, tracking=True)

    notes = fields.Text(string='Notes')

    @api.depends('billing_month')
    def _compute_billing_month_display(self):
        months_fr = {
            1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
            5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
            9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre',
        }
        for rec in self:
            if rec.billing_month:
                rec.billing_month_display = f"{months_fr[rec.billing_month.month]} {rec.billing_month.year}"
            else:
                rec.billing_month_display = ''

    @api.depends('mission_ids', 'provider_id.monthly_rate', 'commission_rate', 'rate_type')
    def _compute_totals(self):
        for rec in self:
            rec.mission_count = len(rec.mission_ids)
            if rec.rate_type == 'monthly':
                # Forfait fixe mensuel défini sur le prestataire
                total = rec.provider_id.monthly_rate if rec.provider_id else 0.0
                rec.monthly_rate = total
            else:
                # Somme des montants des missions individuelles
                total = sum(rec.mission_ids.mapped('amount_total'))
                rec.monthly_rate = 0.0
            commission = total * (rec.commission_rate / 100)
            rec.amount_total = total
            rec.commission_amount = commission
            rec.provider_amount = total - commission

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('senclean.monthly.billing') or _('Nouveau')
        return super().create(vals_list)

    def action_collect_missions(self):
        """Rattache automatiquement toutes les missions du mois non encore facturées."""
        self.ensure_one()
        if not self.billing_month:
            raise UserError(_("Veuillez définir le mois de facturation."))
        month_start = self.billing_month.replace(day=1)
        month_end = month_start + relativedelta(months=1)
        missions = self.env['senclean.mission'].search([
            ('client_id', '=', self.client_id.id),
            ('provider_id', '=', self.provider_id.id),
            ('payment_frequency', '=', 'monthly'),
            ('monthly_billing_id', '=', False),
            ('date_start', '>=', month_start),
            ('date_start', '<', month_end),
            ('state', 'in', ['done', 'in_progress', 'confirmed']),
        ])
        if not missions:
            raise UserError(_("Aucune mission mensuelle non facturée trouvée pour cette période."))
        missions.write({'monthly_billing_id': self.id})
        self.message_post(body=_("%d mission(s) rattachée(s) à cette facturation.") % len(missions))

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Seule une facturation en brouillon peut être confirmée."))
            if not rec.mission_ids:
                raise UserError(_("Rattachez au moins une mission avant de confirmer."))
            rec.state = 'confirmed'
            rec.message_post(body=_("Facturation mensuelle confirmée — montant : %s FCFA") % rec.amount_total)

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("La facturation doit être confirmée avant d'être marquée payée."))
            rec.state = 'paid'
            rec.payment_date = fields.Datetime.now()
            # Marquer toutes les missions liées comme payées
            rec.mission_ids.write({
                'payment_state': 'paid',
                'payment_method': rec.payment_method,
                'payment_ref': rec.name,
                'payment_date': rec.payment_date,
            })
            rec.message_post(body=_("Paiement reçu — %s FCFA via %s") % (
                rec.amount_total, dict(rec._fields['payment_method'].selection).get(rec.payment_method, '')
            ))

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_("Une facturation payée ne peut pas être annulée."))
            # Libérer les missions pour pouvoir les rattacher à une autre facturation
            rec.mission_ids.write({'monthly_billing_id': False})
            rec.state = 'cancelled'
