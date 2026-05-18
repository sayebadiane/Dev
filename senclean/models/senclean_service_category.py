from odoo import models, fields


class SencleanServiceCategory(models.Model):
    _name = 'senclean.service.category'
    _description = 'Catégorie de service SenClean'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    sequence = fields.Integer(string='Ordre', default=10)
    description = fields.Text(string='Description', translate=True)
    icon = fields.Char(string='Icône', help='Classe CSS ou nom icône (ex: ti-home)')
    color = fields.Integer(string='Couleur', default=0)
    service_type = fields.Selection([
        ('recurrent', 'Récurrent'),
        ('ponctuel', 'Ponctuel'),
        ('both', 'Récurrent / Ponctuel'),
    ], string='Type de service', default='both', required=True)
    active = fields.Boolean(default=True)

    provider_ids = fields.Many2many(
        'senclean.provider',
        'senclean_provider_category_rel',
        'category_id', 'provider_id',
        string='Prestataires',
    )
    provider_count = fields.Integer(
        string='Nb prestataires',
        compute='_compute_provider_count',
    )
    mission_count = fields.Integer(
        string='Nb missions',
        compute='_compute_mission_count',
    )

    def _compute_provider_count(self):
        for rec in self:
            rec.provider_count = len(rec.provider_ids.filtered(
                lambda p: p.state == 'active'
            ))

    def _compute_mission_count(self):
        Mission = self.env['senclean.mission']
        for rec in self:
            rec.mission_count = Mission.search_count([
                ('category_id', '=', rec.id)
            ])
