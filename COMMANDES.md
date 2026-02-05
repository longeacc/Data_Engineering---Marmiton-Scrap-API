# Commandes Docker & MongoDB

Ce document récapitule les commandes nécessaires pour configurer, lancer et gérer l'infrastructure Docker du projet Marmiton.

## 1. Démarrage de l'infrastructure

Pour construire les images et lancer tous les services en arrière-plan :

```bash
docker-compose up -d --build
```

Cette commande va :
- Construire les images pour `api` et `webapp`, `loader`.
- Télécharger l'image `mongo`.
- Créer le réseau `data_net`.
- Lancer les conteneurs dans l'ordre de dépendance.

## 2. Vérification

Vérifier que tous les conteneurs tournent correctement :
```bash
docker-compose ps
```

Afficher les logs de tous les services (ou d'un service spécifique) :
```bash
# Tous les logs
docker-compose logs -f

# Logs du loader (pour vérifier l'import des données)
docker-compose logs -f loader

# Logs de l'API
docker-compose logs -f api
```

## 3. Gestion de la Base de Données (MongoDB)

Puisque le port `27017` est exposé sur l'hôte, vous pouvez accéder à MongoDB avec un client externe (comme MongoDB Compass) à l'adresse :
`mongodb://localhost:27017`

Pour accéder au shell MongoDB directement dans le conteneur :
```bash
docker exec -it marmiton_mongo mongosh
```

Une fois dans le shell, quelques commandes utiles :
```javascript
use marmiton_db        // Basculer sur la base de données
show collections       // Voir les collections (tables)
db.recipes.countDocuments() // Compter le nombre de recettes
db.recipes.findOne()   // Voir une recette
```

## 4. Arrêt et Nettoyage

Arrêter les conteneurs :
```bash
docker-compose down
```

Arrêter les conteneurs ET supprimer les volumes (Attention : efface la base de données persistante !) :
```bash
docker-compose down -v
```
