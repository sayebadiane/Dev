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

## 2. `expand="0"` sur `<group>` dans les vues `<search>` — DÉPRÉCIÉ

**Erreur :** `ParseError: Définition de vue invalide`

**Cause :** L'attribut `expand` sur `<group>` dans les vues search a été déprécié en Odoo 17+.

**Fix :** Retirer `expand="0"` et `expand="1"` des éléments `<group>`.

```xml
<!-- INTERDIT -->
<group expand="0" string="Grouper par">

<!-- CORRECT -->
<group string="Grouper par">
```

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

## 4. `category_id` sur `res.groups` — SUPPRIMÉ

**Erreur :** `ValueError: Invalid field 'category_id' in 'res.groups'`

**Cause :** Le champ `category_id` (lien vers `ir.module.category`) a été supprimé du modèle `res.groups` en Odoo 19. La catégorisation des groupes par module n'existe plus.

**Fix :** Supprimer les enregistrements `ir.module.category` et tous les `<field name="category_id">` des groupes.

```xml
<!-- INTERDIT en Odoo 19 -->
<record id="my_category" model="ir.module.category">...</record>
<record id="my_group" model="res.groups">
    <field name="category_id" ref="my_category"/>  <!-- ← SUPPRIMER -->
</record>

<!-- CORRECT -->
<record id="my_group" model="res.groups">
    <field name="name">Mon Groupe</field>
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
