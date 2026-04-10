import pandas as pd
import numpy as np
import time
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

print("Loading Faculty Data...")
# Load faculty dataset
df = pd.read_csv('faculty_data.csv').fillna('')
# We'll use Name, Designation, and Specialisation as the searchable context Document
df['document'] = df['Name'] + " " + df['Designation'] + " " + df['Specialisation']
documents = df['document'].tolist()
# Limit to the first 100 to ensure fast execution and focused baseline for our queries
documents = documents[:100]

print(f"Loaded {len(documents)} faculty profiles.")

# Define some benchmark queries mapping to specific target faculty indices in our 100-doc subset
queries = [
    {"text": "Heat and Mass transfer Differential Equations", "target_idx": 0},          # Dr. Srinivas S
    {"text": "Machine Learning, Deep Learning, Theory of Computation", "target_idx": 3}, # Dr. Sudhakar Ilango
    {"text": "Thermal Engineering, IC Engines", "target_idx": 1},                        # Dr. Dilipkumar Mohanty
    {"text": "Retail Marketing and Entrepreneurship", "target_idx": 6},                  # Dr. Arunkumar Sivakumar
    {"text": "Composites, Biomaterials, Additive Manufacturing", "target_idx": 24},      # Dr. P S Rama Sreekanth
    {"text": "Wireless Sensor Networks Cryptography IoT", "target_idx": 10},             # Dr. Saroj Kumar Panigrahy
    {"text": "Fintech Applications Derivatives", "target_idx": 11},                      # Dr. Raghavendra
]

print("Initializing LSTM Baseline Model...")
# ---------------------------------------------------------
# LSTM PIPELINE
# ---------------------------------------------------------
class BiLSTMEncoder(nn.Module):
    def __init__(self, vocab_size, embed_dim=128, hidden_dim=128):
        super().__init__()
        # Standard embedding layer (initialized randomly for baseline)
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        # Bidirectional LSTM to capture forward and backward context
        self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        
    def forward(self, x):
        embedded = self.embedding(x)
        # outputs shape: (batch, seq_len, num_directions * hidden_dim)
        output, (hn, cn) = self.lstm(embedded)
        # Apply mean pooling across the sequence length to get a single Document Vector
        doc_vector = output.mean(dim=1)
        return doc_vector

# Extremely naive tokenizer and vocabulary builder for the LSTM
vocab = set()
for doc in documents:
    vocab.update(doc.lower().split())
for q in queries:
    vocab.update(q["text"].lower().split())
word2idx = {w: i+1 for i, w in enumerate(vocab)} # 0 is used for padding / unknown

def text_to_tensor(text):
    idxs = [word2idx.get(w.lower(), 0) for w in text.split()]
    if not idxs: idxs = [0]
    return torch.tensor([idxs], dtype=torch.long)

# Initialize untrained BiLSTM (acts as a purely architectural baseline vs a pre-trained Transformer)
lstm_model = BiLSTMEncoder(vocab_size=len(word2idx)+1)
lstm_model.eval()

print("Initializing BERT Pipeline...")
# ---------------------------------------------------------
# BERT PIPELINE (Using the project's chosen MiniLM)
# ---------------------------------------------------------
bert_model = SentenceTransformer('all-MiniLM-L6-v2')

# ---------------------------------------------------------
# EVALUATION ENGINE
# ---------------------------------------------------------
def evaluate_model(model_name, is_bert=True):
    print(f"Evaluating {model_name}...")
    
    # 1. Generate Embeddings for all Documents
    start_doc_time = time.time()
    if is_bert:
        doc_embeddings = bert_model.encode(documents, convert_to_numpy=True)
    else:
        with torch.no_grad():
            doc_embeddings = torch.cat([lstm_model(text_to_tensor(doc)) for doc in documents]).numpy()
    
    # 2. Process Queries and Calculate Metrics
    mrr_sum = 0
    p1_sum = 0
    query_latency_ms = []
    
    for idx, q in enumerate(queries):
        q_start = time.time()
        
        # Get query embedding
        if is_bert:
            q_emb = bert_model.encode([q['text']], convert_to_numpy=True)
        else:
            with torch.no_grad():
                q_emb = lstm_model(text_to_tensor(q['text'])).numpy()
                
        # Calculate Cosine Similarity
        sim_scores = cosine_similarity(q_emb, doc_embeddings)[0]
        
        query_latency_ms.append((time.time() - q_start) * 1000)
        
        # Rank the documents
        ranked_indices = np.argsort(sim_scores)[::-1]
        target_idx = q['target_idx']
        
        # Where did the target document end up in the ranking?
        rank = np.where(ranked_indices == target_idx)[0][0] + 1
        
        # Update metrics
        mrr_sum += 1.0 / rank
        if rank == 1:
            p1_sum += 1

    metrics = {
        'Model': model_name,
        'MRR (Mean Reciprocal Rank)': mrr_sum / len(queries),
        'Precision@1': p1_sum / len(queries),
        'Avg Query Latency (ms)': np.mean(query_latency_ms)
    }
    return metrics

# Run Evaluations
bert_metrics = evaluate_model('BERT (MiniLM)', is_bert=True)
lstm_metrics = evaluate_model('BiLSTM (Baseline)', is_bert=False)

results_df = pd.DataFrame([bert_metrics, lstm_metrics])
print("\n=== Evaluation Results ===")
print(results_df.to_string(index=False))

# ---------------------------------------------------------
# GENERATE GRAPHS FOR THE PAPER
# ---------------------------------------------------------
print("\nGenerating Graphs...")
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Plot 1: MRR
sns.barplot(x='Model', y='MRR (Mean Reciprocal Rank)', data=results_df, ax=axes[0], palette="viridis")
axes[0].set_title('Mean Reciprocal Rank (Higher is Better)', fontsize=14)
axes[0].set_ylim(0, 1.1)

# Plot 2: Precision@1
sns.barplot(x='Model', y='Precision@1', data=results_df, ax=axes[1], palette="magma")
axes[1].set_title('Precision@1 (Higher is Better)', fontsize=14)
axes[1].set_ylim(0, 1.1)

# Plot 3: Latency
sns.barplot(x='Model', y='Avg Query Latency (ms)', data=results_df, ax=axes[2], palette="cubehelix")
axes[2].set_title('Average Query Latency in ms (Lower is Better)', fontsize=14)

plt.suptitle('Comparative Evaluation: BERT vs LSTM for Faculty Recommendation', fontsize=16)
plt.tight_layout()

# Save the figure
graph_path = 'bert_vs_lstm_results.png'
plt.savefig(graph_path, dpi=300)
print(f"Graphs successfully saved to {graph_path}")
