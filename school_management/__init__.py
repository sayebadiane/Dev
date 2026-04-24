from . import models


def post_init_hook(env):
    """Ajoute tous les utilisateurs admin au groupe Directeur à l'installation."""
    manager_group = env.ref('school_management.group_school_manager', raise_if_not_found=False)
    if manager_group:
        admin_users = env['res.users'].search([
            ('all_group_ids', 'in', [env.ref('base.group_system').id]),
            ('active', '=', True),
        ])
        if admin_users:
            admin_users.write({'group_ids': [(4, manager_group.id)]})
