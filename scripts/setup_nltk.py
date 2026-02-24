import nltk

def setup_nlp_assets():
    print("Starting NLTK Resource Download")
    resources = ['punkt', 'stopwords', 'vader_lexicon']
    
    for resource in resources:
        print(f"Downloading {resource}...")
        nltk.download(resource)
    
    print("All NLP assets are ready to use!")

if __name__ == "__main__":
    setup_nlp_assets()