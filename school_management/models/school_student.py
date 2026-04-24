from odoo import models, fields, api
from datetime import date


class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'Élève'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'          # doit pointer vers un champ non-calculé en Odoo 17+
    _order = 'name, firstname'

    name = fields.Char('Nom', required=True, tracking=True)
    firstname = fields.Char('Prénom', required=True, tracking=True)
    full_name = fields.Char('Nom complet', compute='_compute_full_name', store=True)
    registration_number = fields.Char('Matricule', readonly=True, copy=False, default='/')
    photo = fields.Image('Photo', max_width=256, max_height=256)
    date_of_birth = fields.Date('Date de naissance')
    age = fields.Integer('Âge', compute='_compute_age', store=False)
    gender = fields.Selection([
        ('male', 'Masculin'),
        ('female', 'Féminin'),
    ], string='Sexe', tracking=True)
    address = fields.Text('Adresse')
    phone = fields.Char('Téléphone élève')
    class_id = fields.Many2one('school.class', string='Classe', tracking=True)
    school_year = fields.Char('Année scolaire', related='class_id.school_year', store=True)
    state = fields.Selection([
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
    ], string='Statut', default='active', tracking=True)
    parent_ids = fields.Many2many(
        'school.parent', 'student_parent_rel',
        'student_id', 'parent_id', string='Parents / Tuteurs'
    )
    payment_ids = fields.One2many('school.payment', 'student_id', string='Paiements')
    absence_ids = fields.One2many('school.absence', 'student_id', string='Absences')
    bulletin_ids = fields.One2many('school.bulletin', 'student_id', string='Bulletins')

    payment_count = fields.Integer('Paiements', compute='_compute_counts')
    absence_count = fields.Integer('Absences', compute='_compute_counts')
    bulletin_count = fields.Integer('Bulletins', compute='_compute_counts')
    unpaid_amount = fields.Float('Impayés (FCFA)', compute='_compute_unpaid', store=True)
    note = fields.Text('Notes internes')

    @api.depends('name', 'firstname')
    def _compute_full_name(self):
        for rec in self:
            rec.full_name = f"{rec.firstname} {rec.name}" if rec.firstname else (rec.name or '')

    @api.depends('name', 'firstname')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.firstname} {rec.name}" if rec.firstname else (rec.name or '')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0

    @api.depends('payment_ids', 'absence_ids', 'bulletin_ids')
    def _compute_counts(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)
            rec.absence_count = len(rec.absence_ids.filtered(lambda a: not a.is_present))
            rec.bulletin_count = len(rec.bulletin_ids)

    @api.depends('payment_ids.amount_remaining')
    def _compute_unpaid(self):
        for rec in self:
            rec.unpaid_amount = sum(rec.payment_ids.mapped('amount_remaining'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('registration_number', '/') == '/':
                vals['registration_number'] = self.env['ir.sequence'].next_by_code('school.student') or '/'
        return super().create(vals_list)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_deactivate(self):
        self.write({'state': 'inactive'})

    def action_view_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Paiements',
            'res_model': 'school.payment',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    def action_view_absences(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Absences',
            'res_model': 'school.absence',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    def action_view_bulletins(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bulletins',
            'res_model': 'school.bulletin',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }
