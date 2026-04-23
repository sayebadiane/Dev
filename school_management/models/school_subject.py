from odoo import models, fields


class SchoolSubject(models.Model):
    _name = 'school.subject'
    _description = 'Matière scolaire'
    _order = 'name'

    name = fields.Char('Matière', required=True)
    code = fields.Char('Code', size=10)
    coefficient = fields.Float('Coefficient par défaut', default=1.0)
    teacher_id = fields.Many2one('res.users', string='Professeur assigné')
    active = fields.Boolean('Actif', default=True)
    color = fields.Integer('Couleur')
