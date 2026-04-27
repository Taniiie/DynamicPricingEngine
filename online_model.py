"""online_model.py
A simple online model wrapper using `river`. It learns streaming mapping from feature vector -> conversion probability.
For demo we implement a naive logistic regression using river.linear_model.LogisticRegression
"""
from river import linear_model, preprocessing, optim
from river import compose

class OnlinePricingModel:
    def __init__(self):
        # pipeline: standard scaler + logistic regression
        self.model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.LogisticRegression()
        )

    def predict(self, features: dict) -> float:
        # expects features as numeric dict; returns probability in [0,1]
        # For demo: use a very simple heuristic if model not trained
        try:
            # river predict_proba_one expects categorical keys removed; ensure numeric
            # We copy and filter just in case, though caller should provide numeric features
            clean_feats = {k: v for k, v in features.items() if isinstance(v, (int, float))}
            
            prob = self.model.predict_proba_one(clean_feats)
            if isinstance(prob, dict):
                # binary -> get positive class prob
                return prob.get(True, prob.get(1, 0.0))
            # if numeric
            return float(prob)
        except Exception:
            # heuristic fallback
            base = features.get('views_5m', 1) / (1 + features.get('avg_comp_price', features.get('price', 1)))
            return min(0.9, max(0.01, base / 10.0))

    def learn(self, features: dict, target: int):
        # target is 0/1 for conversion event
        clean_feats = {k: v for k, v in features.items() if isinstance(v, (int, float))}
        self.model.learn_one(clean_feats, target)
