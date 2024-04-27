import pandas as pd
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
import numpy as np

def get_rfm(customers_df, products_df, orders_df):
    # Ensure correct data types
    orders_df['OrderDate'] = pd.to_datetime(orders_df['OrderDate'], errors='coerce')
    orders_df.dropna(subset=['OrderDate'], inplace=True)  # Handle missing dates

    # Join orders with customers and products
    orders_df = orders_df.merge(customers_df, on="CustomerID", how='inner')
    orders_df = orders_df.merge(products_df, on="ProductID", how='inner')

    # Calculate total price for each order
    orders_df['TotalPrice'] = orders_df['Price'] * orders_df['Quantity']

    # Calculate Recency, Frequency, and Monetary values
    current_date = datetime.now()
    rfm_table = orders_df.groupby('CustomerID').agg({
        'OrderDate': lambda x: (current_date - x.max()).days,
        'OrderID': 'count',
        'TotalPrice': 'sum'
    }).rename(columns={'OrderDate': 'Recency', 'OrderID': 'Frequency', 'TotalPrice': 'Monetary'})

    # Calculate RFM Score
    rfm_table['R_Score'] = pd.qcut(rfm_table['Recency'], 4, labels=range(4, 0, -1))
    rfm_table['F_Score'] = pd.qcut(rfm_table['Frequency'], 4, labels=range(1, 5))
    rfm_table['M_Score'] = pd.qcut(rfm_table['Monetary'], 4, labels=range(1, 5))
    rfm_table['RFM_Score'] = rfm_table['R_Score'].astype(str) + rfm_table['F_Score'].astype(str) + rfm_table['M_Score'].astype(str)

    # Merge RFM score back to the customer DataFrame
    customer_rfm = customers_df.merge(rfm_table, on='CustomerID', how='inner')
    return customer_rfm

    




def get_clusters(df):
    # Impute missing values
    imputer = SimpleImputer(strategy='mean')
    rfm = df[['Recency', 'Frequency', 'Monetary']]
    rfm_imputed = imputer.fit_transform(rfm)

    # Standardize the data
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm_imputed)

    # Cluster with different k values
    for k in range(3, 7):  # Example: trying 3 to 6 clusters
        kmeans = KMeans(n_clusters=k, random_state=1)
        df['Cluster'] = kmeans.fit_predict(rfm_scaled)
        cluster_summary = df.groupby('Cluster').agg({
            'Recency': 'mean',
            'Frequency': 'mean',
            'Monetary': ['mean', 'count']
        }).round(2)
        print(f"Cluster Summary for {k} Clusters:")
        print(cluster_summary)
        print("\n")

    # Optionally, save the data with the chosen number of clusters
    k_selected = 5  # Example: Suppose you decide that 5 clusters are optimal
    kmeans = KMeans(n_clusters=k_selected, random_state=1)
    df['Cluster'] = kmeans.fit_predict(rfm_scaled)
    df = df[['CustomerID','Recency','Frequency','Monetary','R_Score','F_Score','M_Score','RFM_Score','Cluster']]
    df.to_csv("Customer_RFM_Clusters.csv", index=False)
    return df

def classify_churn_risk(rfm_table):
    # Example risk levels based on RFM quartiles
    conditions = [
        (rfm_table['R_Score'] <= 2) & (rfm_table['F_Score'] <= 2) & (rfm_table['M_Score'] <= 2),
        (rfm_table['R_Score'] >= 3)
    ]
    # Labels for risk levels
    values = ['High Risk', 'Low Risk']
    default_value = 'Medium Risk'
    
    # Create a new column for churn risk level
    rfm_table['ChurnRiskLevel'] = np.select(conditions, values, default=default_value)
    return rfm_table


def churn_rate_by_risk_level(rfm_table):
    # Calculate churn rate by risk level
    risk_level_summary = rfm_table.groupby('ChurnRiskLevel').agg({
        'CustomerID': 'count'
    }).rename(columns={'CustomerID': 'Count'})
    total_customers = rfm_table['CustomerID'].count()
    risk_level_summary['ChurnRate'] = (risk_level_summary['Count'] / total_customers) * 100
    risk_level_summary['ChurnRate'] = risk_level_summary['ChurnRate'].round(2)
    
    return risk_level_summary[['ChurnRate']]