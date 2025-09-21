"""
Legal Document Severity Classification System - Clustering Engine

This module implements the clustering engine for creating semantic buckets from document embeddings.
Uses scikit-learn KMeans clustering with automatic cluster number determination.
"""

from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
import logging
from dataclasses import dataclass

from legal_models import Document, Bucket

logger = logging.getLogger(__name__)


@dataclass
class ClusteringResult:
    """Result of clustering operation."""
    cluster_labels: List[int]
    centroids: List[List[float]]
    n_clusters: int
    silhouette_score: float
    inertia: float


@dataclass
class OptimalClustersResult:
    """Result of optimal cluster number determination."""
    optimal_k: int
    scores: Dict[int, float]
    method_used: str
    elbow_point: Optional[int] = None


class ClusteringEngine:
    """
    Clustering engine for creating semantic buckets from document embeddings.
    
    Uses KMeans clustering with automatic cluster number determination via
    elbow method and silhouette analysis.
    """
    
    def __init__(
        self,
        min_clusters: int = 2,
        max_clusters: int = 20,
        random_state: int = 42,
        max_iter: int = 300,
        n_init: int = 10
    ):
        """
        Initialize the clustering engine.
        
        Args:
            min_clusters: Minimum number of clusters to consider
            max_clusters: Maximum number of clusters to consider
            random_state: Random state for reproducibility
            max_iter: Maximum iterations for KMeans
            n_init: Number of random initializations for KMeans
        """
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters
        self.random_state = random_state
        self.max_iter = max_iter
        self.n_init = n_init
        
    def cluster_documents(
        self,
        embeddings: List[List[float]],
        n_clusters: Optional[int] = None
    ) -> ClusteringResult:
        """
        Cluster document embeddings using KMeans.
        
        Args:
            embeddings: List of document embedding vectors
            n_clusters: Number of clusters (if None, will be determined automatically)
            
        Returns:
            ClusteringResult with cluster labels and centroids
            
        Raises:
            ValueError: If embeddings are empty or invalid
        """
        if not embeddings:
            raise ValueError("Embeddings list cannot be empty")
        
        if len(embeddings) < self.min_clusters:
            raise ValueError(f"Need at least {self.min_clusters} documents for clustering")
        
        # Convert to numpy array and normalize
        X = np.array(embeddings)
        if X.ndim != 2:
            raise ValueError("Embeddings must be 2D array")
        
        # Normalize embeddings for better cosine similarity behavior
        X_normalized = normalize(X, norm='l2')
        
        # Determine optimal number of clusters if not provided
        if n_clusters is None:
            optimal_result = self.find_optimal_clusters(X_normalized)
            n_clusters = optimal_result.optimal_k
            logger.info(f"Determined optimal clusters: {n_clusters} using {optimal_result.method_used}")
        
        # Perform clustering
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=self.random_state,
            max_iter=self.max_iter,
            n_init=self.n_init
        )
        
        cluster_labels = kmeans.fit_predict(X_normalized)
        centroids = kmeans.cluster_centers_.tolist()
        
        # Calculate silhouette score
        if n_clusters > 1:
            sil_score = silhouette_score(X_normalized, cluster_labels)
        else:
            sil_score = 0.0
        
        return ClusteringResult(
            cluster_labels=cluster_labels.tolist(),
            centroids=centroids,
            n_clusters=n_clusters,
            silhouette_score=sil_score,
            inertia=kmeans.inertia_
        )
    
    def find_optimal_clusters(self, embeddings: np.ndarray) -> OptimalClustersResult:
        """
        Find optimal number of clusters using elbow method and silhouette analysis.
        
        Args:
            embeddings: Normalized embedding matrix
            
        Returns:
            OptimalClustersResult with optimal k and scores
        """
        n_samples = len(embeddings)
        max_k = min(self.max_clusters, n_samples - 1)
        
        if max_k < self.min_clusters:
            return OptimalClustersResult(
                optimal_k=self.min_clusters,
                scores={self.min_clusters: 0.0},
                method_used="minimum_fallback"
            )
        
        # Calculate scores for different k values
        inertias = {}
        silhouette_scores = {}
        
        for k in range(self.min_clusters, max_k + 1):
            kmeans = KMeans(
                n_clusters=k,
                random_state=self.random_state,
                max_iter=self.max_iter,
                n_init=self.n_init
            )
            labels = kmeans.fit_predict(embeddings)
            
            inertias[k] = kmeans.inertia_
            if k > 1:
                silhouette_scores[k] = silhouette_score(embeddings, labels)
            else:
                silhouette_scores[k] = 0.0
        
        # Find elbow point
        elbow_k = self._find_elbow_point(inertias)
        
        # Find best silhouette score
        best_silhouette_k = max(silhouette_scores.keys(), key=lambda k: silhouette_scores[k])
        
        # Choose optimal k based on combined criteria
        optimal_k = self._choose_optimal_k(elbow_k, best_silhouette_k, silhouette_scores)
        
        method_used = "combined_elbow_silhouette"
        if elbow_k == optimal_k:
            method_used = "elbow_method"
        elif best_silhouette_k == optimal_k:
            method_used = "silhouette_analysis"
        
        return OptimalClustersResult(
            optimal_k=optimal_k,
            scores=silhouette_scores,
            method_used=method_used,
            elbow_point=elbow_k
        )
    
    def _find_elbow_point(self, inertias: Dict[int, float]) -> int:
        """
        Find elbow point in inertia curve using the "elbow method".
        
        Args:
            inertias: Dictionary of k -> inertia values
            
        Returns:
            Optimal k value based on elbow method
        """
        if len(inertias) < 3:
            return min(inertias.keys())
        
        k_values = sorted(inertias.keys())
        inertia_values = [inertias[k] for k in k_values]
        
        # Calculate second derivative to find elbow
        second_derivatives = []
        for i in range(1, len(inertia_values) - 1):
            second_deriv = inertia_values[i-1] - 2*inertia_values[i] + inertia_values[i+1]
            second_derivatives.append(second_deriv)
        
        if not second_derivatives:
            return k_values[0]
        
        # Find the point with maximum second derivative (sharpest bend)
        max_second_deriv_idx = np.argmax(second_derivatives)
        elbow_k = k_values[max_second_deriv_idx + 1]  # +1 because we start from index 1
        
        return elbow_k
    
    def _choose_optimal_k(
        self,
        elbow_k: int,
        silhouette_k: int,
        silhouette_scores: Dict[int, float]
    ) -> int:
        """
        Choose optimal k by combining elbow method and silhouette analysis.
        
        Args:
            elbow_k: Optimal k from elbow method
            silhouette_k: Optimal k from silhouette analysis
            silhouette_scores: All silhouette scores
            
        Returns:
            Final optimal k value
        """
        # If both methods agree, use that value
        if elbow_k == silhouette_k:
            return elbow_k
        
        # If they disagree, prefer the one with better silhouette score
        # but within reasonable range of the elbow point
        candidates = [elbow_k, silhouette_k]
        
        # Add nearby values to elbow point as candidates
        for offset in [-1, 1]:
            candidate = elbow_k + offset
            if candidate in silhouette_scores:
                candidates.append(candidate)
        
        # Remove duplicates and filter valid candidates
        candidates = list(set(candidates))
        candidates = [k for k in candidates if k in silhouette_scores]
        
        if not candidates:
            return elbow_k
        
        # Choose candidate with best silhouette score
        best_k = max(candidates, key=lambda k: silhouette_scores[k])
        
        return best_k
    
    def calculate_cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
            
        Raises:
            ValueError: If embeddings have different dimensions
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimension")
        
        # Convert to numpy arrays and reshape for sklearn
        emb1 = np.array(embedding1).reshape(1, -1)
        emb2 = np.array(embedding2).reshape(1, -1)
        
        # Calculate cosine similarity
        similarity = cosine_similarity(emb1, emb2)[0, 0]
        
        # Ensure result is between 0 and 1 (cosine similarity can be negative)
        return max(0.0, float(similarity))
    
    def calculate_similarity_matrix(
        self,
        embeddings: List[List[float]]
    ) -> np.ndarray:
        """
        Calculate pairwise cosine similarity matrix for embeddings.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Similarity matrix as numpy array
        """
        if not embeddings:
            return np.array([])
        
        X = np.array(embeddings)
        similarity_matrix = cosine_similarity(X)
        
        # Ensure non-negative values
        similarity_matrix = np.maximum(similarity_matrix, 0.0)
        
        return similarity_matrix
    
    def find_most_similar_documents(
        self,
        query_embedding: List[float],
        document_embeddings: List[List[float]],
        document_ids: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find most similar documents to a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            document_embeddings: List of document embeddings
            document_ids: List of document IDs corresponding to embeddings
            top_k: Number of top similar documents to return
            
        Returns:
            List of (document_id, similarity_score) tuples, sorted by similarity
        """
        if len(document_embeddings) != len(document_ids):
            raise ValueError("Number of embeddings must match number of document IDs")
        
        if not document_embeddings:
            return []
        
        # Calculate similarities
        similarities = []
        for i, doc_embedding in enumerate(document_embeddings):
            similarity = self.calculate_cosine_similarity(query_embedding, doc_embedding)
            similarities.append((document_ids[i], similarity))
        
        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def update_centroid(
        self,
        document_embeddings: List[List[float]]
    ) -> List[float]:
        """
        Calculate centroid (mean) of document embeddings.
        
        Args:
            document_embeddings: List of embedding vectors
            
        Returns:
            Centroid embedding vector
            
        Raises:
            ValueError: If embeddings list is empty
        """
        if not document_embeddings:
            raise ValueError("Cannot calculate centroid of empty embeddings list")
        
        # Convert to numpy array and calculate mean
        embeddings_array = np.array(document_embeddings)
        centroid = np.mean(embeddings_array, axis=0)
        
        # Normalize the centroid
        centroid_normalized = normalize(centroid.reshape(1, -1), norm='l2')[0]
        
        return centroid_normalized.tolist()