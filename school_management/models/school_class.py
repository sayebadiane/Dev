from odoo import models, fields, api
from datetime import date


LEVEL_SELECTION = [
    ('cp', 'CP'),
    ('ce1', 'CE1'),
    ('ce2', 'CE2'),
    ('cm1', 'CM1'),
    ('cm2', 'CM2'),
    ('6eme', '6ème'),
    ('5eme', '5ème'),
    ('4eme', '4ème'),
    ('3eme', '3ème'),
    ('2nde', '2nde'),
    ('1ere', '1ère'),
    ('terminale', 'Terminale'),
]


class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'Classe scolaire'
    _order = 'school_year desc, name'

    name = fields.Char('Nom de la classe', required=True)
    level = fields.Selection(LEVEL_SELECTION, string='Niveau', required=True)
    school_year = fields.Char('Année scolaire', required=True, default='2024-2025')
    teacher_id = fields.Many2one('res.users', string='Professeur principal')
    room = fields.Char('Salle')
    capacity = fields.Integer('Capacité max', default=40)
    monthly_fee = fields.Float('Frais de scolarité mensuel')
    student_ids = fields.One2many('school.student', 'class_id', string='Élèves')
    student_count = fields.Integer('Effectif', compute='_compute_student_count', store=True)
    active = fields.Boolean('Active', default=True)

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids.filtered(lambda s: s.state == 'active'))

    def action_view_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Élèves - {self.name}',
            'res_model': 'school.student',
            'view_mode': 'list,form',
            'domain': [('class_id', '=', self.id)],
            'context': {'default_class_id': self.id},
        }

    def action_mark_attendance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Présences - {self.name}',
            'res_model': 'school.absence',
            'view_mode': 'list',
            'domain': [('class_id', '=', self.id)],
            'context': {'default_class_id': self.id},
        }

    def action_create_monthly_payments(self):
        today = date.today()
        month = str(today.month).zfill(2)
        year = str(today.year)

        created = 0
        for student in self.student_ids.filtered(lambda s: s.state == 'active'):
            existing = self.env['school.payment'].search([
                ('student_id', '=', student.id),
                ('month', '=', month),
                ('year', '=', year),
            ], limit=1)
            if not existing:
                self.env['school.payment'].create({
                    'student_id': student.id,
                    'amount_due': self.monthly_fee,
                    'month': month,
                    'year': year,
                })
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Factures créées',
                'message': f'{created} facture(s) créée(s) pour {month}/{year}.',
                'type': 'success',
            }
        }
