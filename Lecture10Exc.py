import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

CLASS_NAMES = ["Setosa", "Versicolor", "Virginica"]
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c"]


# --- Exercise 3: Homemade PCA with NumPy ---
def compute_pca_homemade(data, n_components=2):
    # Step 1: Center data by subtracting the column means
    mean = np.mean(data, axis=0)
    data_centered = data - mean

    # Step 2: Compute covariance matrix (rowvar=False means columns are features)
    cov_matrix = np.cov(data_centered, rowvar=False)

    # Step 3: Compute eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)

    # Step 4: Sort eigenvectors by descending eigenvalues
    idx_sorted = np.argsort(eigenvalues)[::-1]
    sorted_eigenvectors = eigenvectors[:, idx_sorted]

    # Step 5: Select top n_components and project data
    projection_matrix = sorted_eigenvectors[:, :n_components]
    return np.dot(data_centered, projection_matrix)


# --- Exercise 5: Scikit-Learn PCA ---
def compute_pca_scikit(data, n_components=2):
    pca = PCA(n_components=n_components)
    return pca.fit_transform(data)


# --- Exercise 7: Scikit-Learn LDA ---
def compute_lda_scikit(data, labels, n_components=2):
    lda = LinearDiscriminantAnalysis(n_components=n_components)
    return lda.fit_transform(data, labels)


# --- Reusable Plotter for Exercises 4, 6, 8 ---
def plot_reduced_2d(data_2d, title, xlabel="Component 1", ylabel="Component 2"):
    fig, ax = plt.subplots(figsize=(6, 5))
    for i, class_name in enumerate(CLASS_NAMES):
        start_idx, end_idx = i * 50, (i + 1) * 50
        ax.scatter(
            data_2d[start_idx:end_idx, 0],
            data_2d[start_idx:end_idx, 1],
            label=class_name,
            color=COLORS[i],
            alpha=0.8,
            edgecolors="none",
        )
    ax.set_title(title, fontsize=12, pad=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(title="Species")
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()


def main():
    # 1. Load data
    iris = np.loadtxt("iris.dat")
    X = iris[:, 0:4]
    y = iris[:, 4]

    # 3 & 4: Homemade PCA
    X_pca_homemade = compute_pca_homemade(X, n_components=2)
    plot_reduced_2d(
        X_pca_homemade,
        title="Exercise 4: Homemade PCA (NumPy)",
        xlabel="PC1",
        ylabel="PC2",
    )

    # 5 & 6: Scikit-Learn PCA
    X_pca_scikit = compute_pca_scikit(X, n_components=2)
    plot_reduced_2d(
        X_pca_scikit,
        title="Exercise 6: Scikit-Learn PCA",
        xlabel="PC1",
        ylabel="PC2",
    )

    # 7 & 8: Scikit-Learn LDA
    X_lda_scikit = compute_lda_scikit(X, y, n_components=2)
    plot_reduced_2d(
        X_lda_scikit,
        title="Exercise 8: Scikit-Learn LDA",
        xlabel="LD1",
        ylabel="LD2",
    )

    plt.show()


if __name__ == "__main__":
    main()