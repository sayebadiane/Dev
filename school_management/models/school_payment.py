from odoo import models, fields, api
from datetime import date


MONTH_SELECTION = [
    ('01', 'Janvier'), ('02', 'Février'), ('03', 'Mars'),
    ('04', 'Avril'), ('05', 'Mai'), ('06', 'Juin'),
    ('07', 'Juillet'), ('08', 'Août'), ('09', 'Septembre'),
    ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre'),
]


class SchoolPayment(models.Model):
    _name = 'school.payment'
    _description = 'Paiement de scolarité'
    _inherit = ['mail.thread']
    _order = 'year desc, month desc, student_id'

    name = fields.Char('Référence', readonly=True, copy=False, default='/')
    student_id = fields.Many2one('school.student', string='Élève', required=True, tracking=True, ondelete='cascade')
    class_id = fields.Many2one('school.class', string='Classe', related='student_id.class_id', store=True)
    month = fields.Selection(MONTH_SELECTION, string='Mois', required=True)
    year = fields.Char('Année', required=True, default=lambda self: str(date.today().year))
    period = fields.Char('Période', compute='_compute_period', store=True)
    amount_due = fields.Float('Montant dû (FCFA)', required=True)
    amount_paid = fields.Float('Montant payé (FCFA)', compute='_compute_amounts', store=True)
    amount_remaining = fields.Float('Reste à payer (FCFA)', compute='_compute_amounts', store=True)
    state = fields.Selection([
        ('unpaid', 'Impayé'),
        ('partial', 'Partiel'),
        ('paid', 'Payé'),
    ], string='Statut', compute='_compute_state', store=True, tracking=True)
    line_ids = fields.One2many('school.payment.line', 'payment_id', string='Versements')
    due_date = fields.Date('Date limite', default=lambda self: date.today().replace(day=10))
    note = fields.Text('Note')

    @api.depends('month', 'year')
    def _compute_period(self):
        month_labels = dict(MONTH_SELECTION)
        for rec in self:
            rec.period = f"{month_labels.get(rec.month, '')} {rec.year}"

    @api.depends('line_ids.amount')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_paid = sum(rec.line_ids.mapped('amount'))
            rec.amount_remaining = max(0.0, rec.amount_due - rec.amount_paid)

    @api.depends('amount_paid', 'amount_due')
    def _compute_state(self):
        for rec in self:
            if rec.amount_paid <= 0:
                rec.state = 'unpaid'
            elif rec.amount_paid >= rec.amount_due:
                rec.state = 'paid'
            else:
                rec.state = 'partial'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('school.payment') or '/'
        return super().create(vals_list)

    def action_add_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ajouter un versement',
            'res_model': 'school.payment.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_id': self.id,
                'default_amount': self.amount_remaining,
            },
        }

    def action_print_receipt(self):
        return self.env.ref('school_management.action_report_payment_receipt').report_action(self)


class SchoolPaymentLine(models.Model):
    _name = 'school.payment.line'
    _description = 'Versement'
    _order = 'date desc'

    payment_id = fields.Many2one('school.payment', string='Facture', required=True, ondelete='cascade')
    date = fields.Date('Date du versement', required=True, default=fields.Date.today)
    amount = fields.Float('Montant versé (FCFA)', required=True)
    payment_method = fields.Selection([
        ('cash', 'Espèces'),
        ('transfer', 'Virement'),
        ('mobile', 'Mobile Money'),
        ('check', 'Chèque'),
    ], string='Mode de paiement', default='cash')
    received_by = fields.Many2one('res.users', string='Reçu par', default=lambda self: self.env.user)
    note = fields.Char('Référence / Note')
