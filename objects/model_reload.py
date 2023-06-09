"""Function to retrain XGB model for playoffs."""
import os
from objects.trainer import training_dataset
from objects.model import XGBoostModel
import pickle
import itertools


def model_retrain():
    """Retrain model."""
    if os.path.exists("data/best_playoff_model.pickle"):
        with open("data/best_playoff_model.pickle", "rb") as handle:
            best_playoff_model = pickle.load(handle)
        while True:
            update_model = input(
                f"---Currently existing model is trained and has a cross validated test AUC of {best_playoff_model.best_score}.--- \n \n---The current model is trained with settings INJURY_ADJUST = {best_playoff_model.injury_adjusted} and AVG_MIN_PLAYED_CUTOFF = {best_playoff_model.avg_minutes_played_cutoff}.--- \n \n---Note that some of the best nba playoff models range in AUC from 0.58 to 0.62 on average.---\n \n-------------->'Yes' OR 'No': DO YOU WANT TO UPDATE THE CURRENTLY TRAINED MODEL? (THIS WILL TAKE MORE THAN 45 MINUTES): "
            )
            if update_model == "Yes" or update_model == "No":
                break
            raise SystemExit("Improper user input.")
        if update_model == "Yes":
            update_model = True
        else:
            update_model = False
    else:
        message = """There exists no pretrained playoff model.
                Must pull data and train model. This will take ~45 minutes."""
        print(message)
        update_model = True

    # Pull feature data:

    if not update_model:
        exit()

    train_class = training_dataset(since=2000)  # Feel free to change year
    # Load training dataset with linspace of hyperparameters for
    # injury_adjusted and avg_minutes_played_cutoff:
    # Note 1: Features represent summary statistics for player averages
    #         on each team roster ("_H" and "_A") for
    #         variables 'PTS', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A',
    #         'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
    #         'REB', 'AST', 'STL', 'BLK', and 'TOV'. Summary statistics
    #         are only inclusive of players that average
    #         equal or more than avg_minutes_played_cutoff minutes per game.
    #         Finally, if injury_adjusted is True
    #         than players that are or were injured during game time
    #         are also discluded from such summary statistics.
    #         Each feature is formatted "{summary statistic}_{variable}_{H/A}"
    #         (i.e. "mean_AST_H")
    poss_inj_adj = [True, False]
    poss_avg_cut = list(range(0, 15, 5))
    hyperparamter_space = list(itertools.product(poss_inj_adj, poss_avg_cut))
    # Load all possible hyperparameter datasets
    for settings in hyperparamter_space:
        train_class.load_train_data(
            injury_adjusted=settings[0], avg_minutes_played_cutoff=settings[1]
        )

    # Create and train the NBA model
    # Define hyperparameter space:

    hyperparameter_space = {
        "max_depth": [3, 5, 7],
        "learning_rate": [0.001, 0.01, 0.1],
        "n_estimators": [100, 200],
        "min_child_weight": [1, 3],
        "gamma": [0, 0.1],
    }

    print("----->testing all possible cominations now")
    # Load all possible hyperparameter datasets and perform grid search:
    models = []
    for settings in itertools.product(poss_inj_adj, poss_avg_cut):
        print(
            f"-------->Searching for injury adjusted {settings[0]},"
            f"--------> minutes cutoff {settings[1]}"
        )
        xgb_model = XGBoostModel(
            injury_adjusted=settings[0],
            avg_minutes_played_cutoff=settings[1],
            train_class=train_class,
        )
        xgb_model.grid_search(param_grid=hyperparameter_space)
        models.append(xgb_model)
        print(f"Best AUC with CV hyperparameters: {xgb_model.best_score}")
    best_playoff_model = max(models, key=lambda model: model.model.best_score)
    print("Best hyperparameters:", best_playoff_model.model.get_params)
    print("Best AUC score", best_playoff_model.best_score)
    print(
        best_playoff_model.injury_adjusted, best_playoff_model.avg_minutes_played_cutoff
    )

    # Find model with best cross validated test AUC:

    print("Best XGB hyperparameters:", best_playoff_model.model.get_params)
    print("Best AUC score", best_playoff_model.best_score)
    print(
        f"Best training hyperparameters are INJURY_ADJUST = {best_playoff_model.injury_adjusted}, AVG_MIN_CUTOFF = {best_playoff_model.avg_minutes_played_cutoff}"
    )

    # Save model

    with open("data/best_playoff_model.pickle", "wb") as handle:
        pickle.dump(best_playoff_model, handle, protocol=pickle.HIGHEST_PROTOCOL)
