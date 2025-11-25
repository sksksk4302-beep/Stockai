import random
import numpy as np
import pandas as pd
from deap import base, creator, tools, algorithms

# 1. Setup GA Environment
# We want to maximize return (FitnessMax)
# Weights: (Return, -Number_of_Conditions) -> Prefer higher return, simpler rules
creator.create("FitnessMax", base.Fitness, weights=(1.0, -0.1))
creator.create("Individual", list, fitness=creator.FitnessMax)

class GAEngine:
    def __init__(self, df):
        self.df = df
        # Exclude metadata and ANY target variables (data leakage prevention)
        self.features = [col for col in df.columns 
                        if col not in ['date', 'ticker', 'name'] 
                        and not col.startswith('target_')]
        
        print(f"📊 Features available: {len(self.features)}")
        # print(f"Feature list: {self.features}")
        
        # Calculate min/max for each feature to set appropriate threshold ranges
        self.feat_ranges = {}
        for feat in self.features:
            self.feat_ranges[feat] = (df[feat].min(), df[feat].max())
            
        self.toolbox = base.Toolbox()
        self._setup_toolbox()

    def _get_random_threshold(self, feat_idx):
        """Generate a random threshold within the range of the selected feature"""
        feat_name = self.features[feat_idx]
        min_val, max_val = self.feat_ranges[feat_name]
        # Avoid exact min/max to prevent always-true/false rules
        return random.uniform(min_val, max_val)

    def _setup_toolbox(self):
        # Gene: [Feature_Index, Operator(0: <, 1: >), Threshold]
        self.toolbox.register("attr_feat", random.randint, 0, len(self.features)-1)
        self.toolbox.register("attr_op", random.randint, 0, 1)
        # Threshold is now generated dynamically based on the feature
        # We'll use a placeholder here and fix it in the individual creator or mutation
        self.toolbox.register("attr_thres", random.uniform, 0, 1) 
        
        # Condition creator wrapper to handle dynamic threshold
        def create_condition():
            feat_idx = random.randint(0, len(self.features)-1)
            op = random.randint(0, 1)
            thres = self._get_random_threshold(feat_idx)
            return [feat_idx, op, thres]

        self.toolbox.register("condition", create_condition)
        
        # Individual: Variable length list of conditions (1 to 3 conditions)
        self.toolbox.register("individual", tools.initRepeat, creator.Individual, self.toolbox.condition, n=random.randint(1, 3))
        
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        self.toolbox.register("evaluate", self.evaluate)
        self.toolbox.register("mate", self.safe_mate)
        self.toolbox.register("mutate", self.mutate_individual)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    def safe_mate(self, ind1, ind2):
        """Safely mate two individuals, handling variable lengths"""
        if len(ind1) < 2 or len(ind2) < 2:
            # If either is too short for 2-point crossover, swap the whole individuals with probability
            if random.random() < 0.5:
                ind1[:], ind2[:] = ind2[:], ind1[:]
            return ind1, ind2
        
        # Use standard 2-point crossover for longer individuals
        return tools.cxTwoPoint(ind1, ind2)

    def mutate_individual(self, individual):
        """Custom mutation: Modify condition, Add condition, or Remove condition"""
        prob = random.random()
        
        if prob < 0.33 and len(individual) > 1: # Remove condition
            del individual[random.randint(0, len(individual)-1)]
        elif prob < 0.66 and len(individual) < 5: # Add condition
            individual.append(self.toolbox.condition())
        else: # Modify existing condition
            # Mutate one gene in one condition
            cond_idx = random.randint(0, len(individual)-1)
            gene_idx = random.randint(0, 2)
            
            if gene_idx == 0: # Feature
                # When changing feature, we must also reset threshold to match new feature's range
                new_feat_idx = random.randint(0, len(self.features)-1)
                individual[cond_idx][0] = new_feat_idx
                individual[cond_idx][2] = self._get_random_threshold(new_feat_idx)
            elif gene_idx == 1: # Operator
                individual[cond_idx][1] = 1 - individual[cond_idx][1]
            else: # Threshold
                # Add noise but keep within range
                feat_idx = individual[cond_idx][0]
                feat_name = self.features[feat_idx]
                min_val, max_val = self.feat_ranges[feat_name]
                std_dev = (max_val - min_val) * 0.1 # 10% of range as std dev
                
                new_thres = individual[cond_idx][2] + random.gauss(0, std_dev)
                # Clip to range
                new_thres = max(min_val, min(max_val, new_thres))
                individual[cond_idx][2] = new_thres
                
        return individual,

    def evaluate(self, individual):
        """
        Evaluate the profitability of a composite rule (AND logic).
        """
        if not individual:
            return (-999, 0)

        # Start with all True
        combined_signals = pd.Series(True, index=self.df.index)
        
        for cond in individual:
            feat_idx, op, thres = cond
            feature_name = self.features[feat_idx]
            
            try:
                series = self.df[feature_name]
                if op == 0: # <
                    signals = series < thres
                else: # >
                    signals = series > thres
                
                combined_signals = combined_signals & signals
            except:
                return (-999, 0)
        
        # Calculate returns
        try:
            returns = self.df.loc[combined_signals, 'target_return_1d']
            
            if len(returns) < 20: # Minimum trades required
                return (-999, len(individual))
                
            total_return = returns.sum()
            return (total_return, len(individual))
            
        except Exception:
            return (-999, len(individual))

    def run(self, generations=10, population_size=50):
        pop = self.toolbox.population(n=population_size)
        hof = tools.HallOfFame(5)
        
        stats = tools.Statistics(lambda ind: ind.fitness.values[0]) # Track return only
        stats.register("avg", np.mean)
        stats.register("max", np.max)
        
        pop, log = algorithms.eaSimple(pop, self.toolbox, cxpb=0.5, mutpb=0.3, ngen=generations, 
                                       stats=stats, halloffame=hof, verbose=True)
        
        return hof, log

    def decode_rule(self, individual):
        parts = []
        for cond in individual:
            feat_idx, op, thres = cond
            feature_name = self.features[feat_idx]
            op_str = "<" if op == 0 else ">"
            parts.append(f"({feature_name} {op_str} {thres:.4f})")
        return " AND ".join(parts)

if __name__ == "__main__":
    # Mock data for testing
    data = {
        'rsi': np.random.uniform(0, 100, 100),
        'ma5': np.random.uniform(100, 200, 100),
        'target_return_1d': np.random.normal(0, 1, 100)
    }
    df = pd.DataFrame(data)
    
    engine = GAEngine(df)
    best_rules, _ = engine.run(generations=5)
    
    print("\nTop Rules:")
    for rule in best_rules:
        print(f"{engine.decode_rule(rule)} => Fitness: {rule.fitness.values[0]:.2f}")
