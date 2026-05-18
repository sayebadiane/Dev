# Notes de compatibilité Odoo 19 — Erreurs rencontrées

> Environnement : Odoo 19 Community, modules custom développés initialement pour Odoo 16.

---

## 1. `<separator/>` dans les vues `<search>` — SUPPRIMÉ

**Erreur :** `ParseError: Définition de vue invalide`

**Cause :** L'élément `<separator/>` a été retiré des vues `<search>` dans Odoo 17+.

**Fix :** Supprimer toutes les occurrences de `<separator/>` dans les blocs `<search>`.

```xml
<!-- INTERDIT en Odoo 17+ -->
<search>
    <filter .../>
    <separator/>   <!-- ← SUPPRIMER -->
    <filter .../>
</search>

<!-- CORRECT -->
<search>
    <filter .../>
    <filter .../>
</search>
```

---

## 2. `expand` et `string` sur `<group>` dans les vues `<search>` — INVALIDES

**Erreur :** `ParseError: Définition de vue invalide`

**Cause :** Le schéma RelaxNG (`search_view.rng` + `common.rng`) de Odoo 19 n'autorise sur `<group>` que les attributs : `name`, `col`, `colspan`, `rowspan`, `fill`, `height`, `width`, `color`, `invisible`. Les attributs `expand` et `string` sont absents du schéma → la validation RelaxNG échoue silencieusement avec le message générique "Définition de vue invalide".

**Fix :** Supprimer `expand` et `string` des `<group>` dans les vues search. Utiliser `name` si un identifiant est nécessaire.

```xml
<!-- INTERDIT en Odoo 19 — attributs non autorisés par le schéma RNG -->
<group expand="0" string="Grouper par">

<!-- CORRECT — aucun attribut, ou uniquement name -->
<group>
```

> **Piège :** `string` est valide sur `<group>` dans les vues **form**, mais PAS dans les vues **search**. Le schéma est différent selon le type de vue.

---

## 3. `_rec_name` pointant vers un champ calculé — INVALIDE en Odoo 17+

> ⚠️ **PIÈGE** : corriger `_rec_name` ne signifie PAS supprimer le champ calculé.
> Les vues qui utilisent ce champ continueront à en avoir besoin.
> Il faut uniquement changer ce que `_rec_name` pointe — le champ reste dans le modèle.

**Erreur :** `ParseError: Définition de vue invalide` sur TOUTES les vues du modèle concerné

**Cause :** En Odoo 17+, `_rec_name` doit pointer vers un champ **non-calculé** (stocké en DB sans `compute`). Si `_rec_name` pointe vers un champ `compute=`, la validation des vues échoue pour tout le modèle.

**Fix :**
```python
# INTERDIT en Odoo 17+
_rec_name = 'full_name'  # si full_name est un champ compute

# CORRECT
_rec_name = 'name'  # champ concret non-calculé

# Pour garder un affichage personnalisé, surcharger _compute_display_name :
def _compute_display_name(self):
    for rec in self:
        rec.display_name = f"{rec.firstname} {rec.name}" if rec.firstname else rec.name
```

> `_compute_display_name` remplace `name_get()` qui est déprécié depuis Odoo 17.

---

## 4. Champs calculés (`compute`) dans `<field>` des vues `<search>` — INVALIDE

**Erreur :** `ParseError: Définition de vue invalide`

**Cause :** En Odoo 19, un champ calculé (même avec `store=True`) utilisé dans un élément `<field>` d'une vue search est rejeté par le validateur s'il n'a pas de méthode `_search` explicite.

**Fix :** Remplacer par le(s) champ(s) concret(s) sous-jacents avec `filter_domain`.

```xml
<!-- INTERDIT si full_name est calculé -->
<field name="full_name" string="Nom complet"/>

<!-- CORRECT : utiliser les champs sources avec filter_domain -->
<field name="name" string="Nom / Prénom"
       filter_domain="['|', ('name', 'ilike', self), ('firstname', 'ilike', self)]"/>
```

---

## 4b. Champs `Many2many` dans `<field>` des vues `<search>` — filter_domain obligatoire

**Erreur :** `ParseError: Définition de vue invalide`

**Cause :** En Odoo 19, un champ `Many2many` utilisé dans `<field>` d'une vue search sans `filter_domain` est invalide. Odoo ne sait pas comment construire le domaine de recherche automatiquement pour ce type de relation.

**Fix :** Ajouter `filter_domain` qui cible le nom de la catégorie liée.

```xml
<!-- INTERDIT en Odoo 19 -->
<field name="category_ids" string="Catégorie"/>

<!-- CORRECT -->
<field name="category_ids" string="Catégorie"
       filter_domain="[('category_ids.name', 'ilike', self)]"/>
```

---

## 4c. `group_by` sur un champ `Many2many` — NON SUPPORTÉ

**Erreur :** `ParseError: Définition de vue invalide`

**Cause :** Odoo ne supporte pas le regroupement (`group_by`) sur un champ `Many2many`. La valeur dans `context="{'group_by':'mon_champ_m2m'}"` est ignorée ou provoque une erreur de validation de vue.

**Fix :** Supprimer le filtre de regroupement sur les Many2many. Utiliser uniquement `group_by` sur des champs `Many2one`, `Selection`, `Char`, `Date`.

```xml
<!-- INTERDIT -->
<filter name="group_category" context="{'group_by':'category_ids'}"/>

<!-- CORRECT : utiliser uniquement Many2one ou Selection -->
<filter name="group_category" context="{'group_by':'category_id'}"/>
```

---

## 4d. `datetime.datetime.now()` dans les domaines de filtres — À ÉVITER

**Cause :** `datetime.datetime.now()` retourne l'heure serveur UTC, sans tenir compte du fuseau horaire de l'utilisateur. En Odoo 19, l'expression peut aussi ne pas être évaluée correctement selon le contexte.

**Fix :** Utiliser `context_today()` qui retourne la date courante dans le fuseau de l'utilisateur.

```xml
<!-- DÉCONSEILLÉ -->
<filter domain="[('date_start', '>=', datetime.datetime.now().strftime('%Y-%m-%d 00:00:00'))]"/>

<!-- CORRECT -->
<filter domain="[('date_start', '>=', context_today().strftime('%Y-%m-%d 00:00:00')),
                  ('date_start', '<=', context_today().strftime('%Y-%m-%d 23:59:59'))]"/>
```

---

## 4. `category_id` et `users` sur `res.groups` — SUPPRIMÉS

**Erreur :** `ValueError: Invalid field 'category_id' in 'res.groups'`
**Erreur :** `ValueError: Invalid field 'users' in 'res.groups'`

**Cause :** En Odoo 19, deux champs ont été supprimés du modèle `res.groups` :
- `category_id` (lien vers `ir.module.category`) — la catégorisation des groupes par module n'existe plus
- `users` (Many2many vers `res.users`) — l'assignation directe d'utilisateurs à un groupe via XML n'est plus supportée

**Fix :** Supprimer les enregistrements `ir.module.category`, tous les `<field name="category_id">` et tous les `<field name="users">` des groupes. L'assignation des utilisateurs aux groupes se fait uniquement via l'interface ou via `res.users`.

```xml
<!-- INTERDIT en Odoo 19 -->
<record id="my_category" model="ir.module.category">...</record>
<record id="my_group" model="res.groups">
    <field name="category_id" ref="my_category"/>     <!-- ← SUPPRIMER -->
    <field name="users" eval="[(4, ref('base.user_admin'))]"/>  <!-- ← SUPPRIMER -->
</record>

<!-- CORRECT en Odoo 19 -->
<record id="my_group" model="res.groups">
    <field name="name">Mon Groupe</field>
    <field name="implied_ids" eval="[(4, ref('autre_group'))]"/>  <!-- OK -->
</record>
```

---

## 5. Ordre de déclaration des groupes dans `school_security.xml` — REF FORWARD

**Erreur :** `ValueError: External ID not found in the system: school_management.group_X`

**Cause :** Un groupe référence via `ref()` un autre groupe déclaré plus bas dans le même fichier. Odoo charge les records séquentiellement — une `ref()` ne peut pointer que vers un record déjà créé.

**Fix :** Déclarer les groupes du moins privilégié au plus privilégié.

```xml
<!-- ORDRE CORRECT (du moins au plus privilégié) -->
<record id="group_teacher" .../>      <!-- 1. base, sans dépendance -->
<record id="group_secretary" ...>
    <field name="implied_ids" eval="[(4, ref('group_teacher'))]"/>  <!-- OK -->
</record>
<record id="group_manager" ...>
    <field name="implied_ids" eval="[(4, ref('group_secretary'))]"/>  <!-- OK -->
</record>
```

---

## 6. Ordre de chargement dans `__manifest__.py` — DASHBOARD EN DERNIER

**Erreur :** `ValueError: External ID not found in the system: module.action_xxx`

**Cause :** Les boutons dans les vues `<arch>` utilisent `%(xml_id)d` pour référencer des actions. Ces références sont résolues au moment du chargement XML. Si le fichier du dashboard est chargé avant les fichiers qui définissent les actions, la résolution échoue.

**Fix :** Toujours charger le dashboard après tous les fichiers qui définissent des actions.

```python
# __manifest__.py — ORDRE CORRECT
'data': [
    'security/...',
    'data/...',
    'views/model_a_views.xml',   # définit action_a
    'views/model_b_views.xml',   # définit action_b
    'views/dashboard_views.xml', # ← EN DERNIER (référence action_a, action_b)
    'views/menus.xml',
]
```

---

## 7. Vue kanban — Syntaxe `t-name` changée

**Ancienne syntaxe (Odoo 16) :**
```xml
<t t-name="kanban-box">
    <div class="oe_kanban_card oe_kanban_global_click">...</div>
</t>
```

**Nouvelle syntaxe (Odoo 17+) :**
```xml
<t t-name="card" class="flex-row">
    <aside><field name="photo" widget="image"/></aside>
    <main>...</main>
</t>
```

---

## 8. Assets — Cache désynchronisé (`AssetsLoadingError`)

**Erreur :** `AssetsLoadingError: The loading of /web/assets/HASH/bundle.min.js failed`

**Cause :** Les bundles JS/CSS sont compilés avec des hashes différents (modules installés à des moments différents). La base garde les anciens hashes en cache dans `ir.attachment`.

**Fix :**
```sql
-- Vider le cache assets en base
DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';
```
Puis relancer Odoo :
```bash
python odoo-bin -d <base> --dev=all
```

---

## 9. `<tree>` renommé en `<list>` — Odoo 17+

```xml
<!-- INTERDIT en Odoo 17+ -->
<tree string="...">

<!-- CORRECT -->
<list string="...">
```

---

## 10. Import datetime dans les méthodes — Bonne pratique

**Problème :** `from datetime import date` placé à l'intérieur d'une méthode.

**Fix :** Toujours mettre les imports en haut du fichier Python.

```python
# CORRECT
from odoo import models, fields, api
from datetime import date   # ← en haut du fichier

class MyModel(models.Model):
    def my_method(self):
        today = date.today()  # ← pas d'import ici
```

---

## 11. `implied_ids` dans `res.groups` — Sens à ne pas inverser

**Symptôme :** Le menu de l'application est invisible pour l'admin après installation, même avec le bon groupe sur le menu.

**Cause :** Confusion sur le sens de `implied_ids` :
- `group_A.implied_ids = [group_B]` signifie : **"être dans A implique aussi avoir B"**
- Ce n'est PAS "être dans B implique avoir A"

Si on écrit `group_senclean_user.implied_ids = [(4, base.group_user)]`, ça dit qu'un utilisateur SenClean est aussi un utilisateur interne — mais l'admin n'est **pas** automatiquement dans SenClean.

**Fix :** Faire l'inverse : étendre `base.group_user` pour qu'il implique ton groupe applicatif. Ainsi, tout utilisateur interne Odoo (dont l'admin) accède automatiquement à l'application.

```xml
<!-- INCORRECT — l'admin ne voit pas le menu -->
<record id="group_senclean_user" model="res.groups">
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
</record>

<!-- CORRECT — tout utilisateur interne voit automatiquement l'app -->
<record id="group_senclean_user" model="res.groups">
    <field name="name">SenClean / Utilisateur</field>
    <!-- pas de implied_ids ici -->
</record>

<!-- On étend base.group_user pour qu'il implique notre groupe -->
<record id="base.group_user" model="res.groups">
    <field name="implied_ids" eval="[(4, ref('group_senclean_user'))]"/>
</record>
```

> Ce pattern est utilisé par tous les modules Odoo natifs (CRM, Ventes, etc.) pour rendre l'app accessible à tous les utilisateurs internes par défaut.

---

## 13. `groups_id` renommé `group_ids` sur `res.users` — Odoo 19

**Erreur :** `ValueError: Invalid field 'groups_id' in 'res.users'`

**Cause :** Le champ Many2many des groupes sur `res.users` a été renommé de `groups_id` en `group_ids` dans Odoo 19.

**Fix :**
```python
# INTERDIT en Odoo 19
user.write({'groups_id': [(4, portal_group.id)]})
User.create({'groups_id': [(6, 0, [portal_group.id])]})

# CORRECT en Odoo 19
user.write({'group_ids': [(4, portal_group.id), (3, group_public.id)]})
```

**Création d'un utilisateur portail — méthode officielle Odoo 19 :**
```python
from odoo.tools.mail import email_normalize

User.with_context(no_reset_password=True)._create_user_from_template({
    'email': email_normalize(email),
    'login': email_normalize(email),
    'partner_id': partner.id,
    'company_id': env.company.id,
    'company_ids': [(6, 0, env.company.ids)],
})
```
> Ne pas utiliser `res.users.create()` directement pour les comptes portail — utiliser `_create_user_from_template` qui applique le bon template avec les groupes corrects.

---

## 12. `mail.activity.mixin` ne dépend plus de `mail.thread` — Odoo 19

**Erreur :** `AttributeError: 'monmodele' object has no attribute '_get_thread_with_access'`

**Cause :** En Odoo 19, `mail.activity.mixin` est devenu un **AbstractModel standalone** : il n'hérite plus de `mail.thread`. La méthode `_get_thread_with_access` (utilisée par le chatter) appartient à `mail.thread`. Si un modèle n'hérite que de `mail.activity.mixin`, il n'a pas ce méthode et le chatter crashe à l'ouverture.

En Odoo 16/17 (avant la rupture) :
```
mail.activity.mixin._inherit = ['mail.thread']  ← chaîne automatique
```

En Odoo 19 :
```
mail.activity.mixin._inherit = []  ← standalone, pas de chaîne
```

**Fix :** Déclarer `mail.thread` explicitement dans `_inherit` des modèles qui ont un chatter.

```python
# INTERDIT en Odoo 19 — mail.thread manquant, _get_thread_with_access absent
_inherit = ['mail.activity.mixin']

# CORRECT — mail.thread déclaré explicitement
_inherit = ['mail.thread', 'mail.activity.mixin']
```

**Règle pour les 3 cas courants :**

| Mixins voulus | `_inherit` correct |
|---|---|
| Chatter + Activités | `['mail.thread', 'mail.activity.mixin']` |
| Chatter + Activités + Notes | `['mail.thread', 'mail.activity.mixin', 'rating.mixin']` ← risque MRO |
| Chatter + Notes (rating.mixin) | `['mail.activity.mixin', 'rating.mixin']` ← mail.thread vient via rating.mixin |

> **Piège MRO :** `rating.mixin` hérite lui-même de `mail.thread`. Si tu listes `mail.thread` **avant** `rating.mixin` dans `_inherit`, Python lève `TypeError: Cannot create a consistent MRO`. Toujours mettre `rating.mixin` en dernier, ou ne pas re-déclarer `mail.thread` quand `rating.mixin` est présent.
