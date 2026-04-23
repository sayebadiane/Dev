from odoo import models, fields, api


class SchoolParent(models.Model):
    _name = 'school.parent'
    _description = 'Parent / Tuteur'
    _inherit = ['mail.thread']
    _rec_name = 'name'   # champ non-calculé ; display_name est surchargé ci-dessous
    _order = 'name'

    name = fields.Char('Nom', required=True, tracking=True)
    firstname = fields.Char('Prénom', required=True, tracking=True)
    full_name = fields.Char('Nom complet', compute='_compute_full_name', store=True)
    relationship = fields.Selection([
        ('father', 'Père'),
        ('mother', 'Mère'),
        ('guardian', 'Tuteur légal'),
        ('other', 'Autre'),
    ], string='Lien de parenté', default='father')
    phone = fields.Char('Téléphone', tracking=True)
    phone2 = fields.Char('Téléphone 2')
    email = fields.Char('Email', tracking=True)
    address = fields.Text('Adresse')
    profession = fields.Char('Profession')
    student_ids = fields.Many2many(
        'school.student', 'student_parent_rel',
        'parent_id', 'student_id', string='Enfants'
    )
    student_count = fields.Integer('Nb enfants', compute='_compute_student_count')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.firstname} {rec.name}" if rec.firstname else (rec.name or '')

    @api.depends('name', 'firstname')
    def _compute_full_name(self):
        for rec in self:
            rec.full_name = f"{rec.firstname} {rec.name}" if rec.firstname else rec.name

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    def action_view_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enfants',
            'res_model': 'school.student',
            'view_mode': 'list,form',
            'domain': [('parent_ids', 'in', [self.id])],
            'context': {'default_parent_ids': [(4, self.id)]},
        }
