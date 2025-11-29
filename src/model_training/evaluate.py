from sklearn.metrics import roc_auc_score, classification_report


def evaluate_model(model, X_test, y_test):
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    print("ROC-AUC:", auc)
    print(classification_report(y_test, (y_prob > 0.5).astype(int)))
    return auc
