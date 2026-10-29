import pandas as pd, numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, PolynomialFeatures
from sklearn.linear_model import LinearRegression, RidgeCV, LassoCV
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.decomposition import PCA

def run_analysis(df, target):
    X, y = df.drop(columns=[target]), df[target]
    num = X.select_dtypes('number').columns
    cat = X.select_dtypes(exclude='number').columns

    prep = ColumnTransformer([
        ('num', Pipeline([('imp', SimpleImputer(strategy='median')),
                          ('sc', StandardScaler())]), num),
        ('cat', Pipeline([('imp', SimpleImputer(strategy='most_frequent')),
                          ('oh', OneHotEncoder(handle_unknown='ignore',
                                               max_categories=20))]), cat),
    ])

    models = {
        'Linear':     Pipeline([('p', prep), ('m', LinearRegression())]),
        'Ridge':      Pipeline([('p', prep), ('m', RidgeCV(alphas=np.logspace(-2, 3, 20)))]),
        'Lasso':      Pipeline([('p', prep), ('m', LassoCV(cv=5, max_iter=5000))]),
        'Polynomial': Pipeline([('p', prep), ('poly', PolynomialFeatures(2, include_bias=False)),
                                ('sel', SelectKBest(f_regression, k=50)),
                                ('m', RidgeCV(alphas=np.logspace(-2, 3, 20)))]),
        'PCA + Ridge':Pipeline([('p', prep), ('pca', PCA(0.95)),
                                ('m', RidgeCV(alphas=np.logspace(-2, 3, 20)))]),
    }

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    results = {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        results[name] = round(m.score(Xte, yte), 3)   # R² on unseen data
    return results