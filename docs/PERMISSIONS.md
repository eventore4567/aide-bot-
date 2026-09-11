# Permissions

Aide Bot utilise un modèle **fail-closed** : une action sensible inconnue ou non explicitement autorisée est refusée.

## Capacités

| Capacité | Helper | Formateur | Resp. Formation | Direction |
|---|---:|---:|---:|---:|
| `help.claim` | ✅ | ✅ | ✅ | ✅ |
| `training.claim` | ❌ | ✅ | ✅ | ✅ |
| `training.manage` | ❌ | ❌ | ✅ | ✅ |
| `payment.confirm` | ❌ | ❌ | ❌ | ✅ |
| `applications.review` | ❌ | ❌ | ✅ | ✅ |
| `config.manage` | ❌ | ❌ | ❌ | ✅ |

Le propriétaire du serveur garde un bypass explicite.

## Principes

- Pas d’Administrateur par facilité.
- Pas de permissions héritées implicitement parce qu’un rôle « semble staff ».
- Vérification de la hiérarchie Discord avant les actions de rôles.
- Tickets visibles uniquement par le client et les rôles nécessaires.
- Les paiements ne peuvent être confirmés que par la Direction.
- `/permissions_test @membre` explique ce que le membre peut réellement faire et pourquoi.
