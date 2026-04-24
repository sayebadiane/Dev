from . import models


def post_init_hook(env):
    """Ajoute tous les utilisateurs internes admin au groupe Directeur à l'installation."""
    manager_group = env.ref('school_management.group_school_manager', raise_if_not_found=False)
    if manager_group:
        admin_users = env['res.users'].search([
            ('groups_id', 'in', [env.ref('base.group_system').id]),
            ('active', '=', True),
        ])
        if admin_users:
            manager_group.write({'users': [(4, uid) for uid in admin_users.ids]})
