import random
import numpy as np
import pandas as pd
from deap import base, creator, tools, algorithms

# 1. Setup GA Environment
# We want to maximize return (FitnessMax)
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

class GAEngine:
    def __init__(self, df):
        self.df = df
        self.features = [col for col in df.columns if col not in ['date', 'ticker', 'name', 'target_return_1d']]
        self.toolbox = base.Toolbox()
        self._setup_toolbox()

    def _setup_toolbox(self):
        # Gene: [Feature_Index, Operator(0: <, 1: >), Threshold]
        self.toolbox.register("attr_feat", random.randint, 0, len(self.features)-1)
        self.toolbox.register("attr_op", random.randint, 0, 1)
        self.toolbox.register("attr_thres", random.uniform, -2.0, 2.0) # Normalized threshold
        
        # Individual: A list of 3 genes (Simple rule: Feature OP Threshold)
        self.toolbox.register("individual", tools.initCycle, creator.Individual,
                             (self.toolbox.attr_feat, self.toolbox.attr_op, self.toolbox.attr_thres), n=1)
        
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        self.toolbox.register("evaluate", self.evaluate)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", tools.mutUniformInt, low=[0,0,-2], up=[len(self.features)-1, 1, 2], indpb=0.2)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    def evaluate(self, individual):
        """
        Evaluate the profitability of a rule.
        Rule: If Feature X (</>) Threshold, then BUY.
        """
        feat_idx, op, thres = individual
        feature_name = self.features[feat_idx]
        
        # Simple Backtest
        # We assume we buy if condition is met, and hold for 1 day
        # Target: target_return_1d (Next day return)
        
        try:
            # Get feature data
            series = self.df[feature_name]
            
            # Apply condition
            if op == 0: # <
                signals = series < thres
            else: # >
                signals = series > thres
                
            # Calculate returns
            # If signal is True, we get target_return_1d
            returns = self.df.loc[signals, 'target_return_1d']
            
            if len(returns) < 10: # Too few trades
                return (-999,)
                
            # Metric: Average Daily Return * sqrt(252) (Annualized Return approximation)
            # Or simply Sum of returns
            total_return = returns.sum()
            
            return (total_return,)
            
        except Exception as e:
            return (-999,)

    def run(self, generations=10, population_size=50):
        pop = self.toolbox.population(n=population_size)
        hof = tools.HallOfFame(5) # Top 5 rules
        
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("max", np.max)
        
        pop, log = algorithms.eaSimple(pop, self.toolbox, cxpb=0.5, mutpb=0.2, ngen=generations, 
                                       stats=stats, halloffame=hof, verbose=True)
        
        return hof, log

    def decode_rule(self, individual):
        feat_idx, op, thres = individual
        feature_name = self.features[feat_idx]
        op_str = "<" if op == 0 else ">"
        return f"{feature_name} {op_str} {thres:.4f}"

if __name__ == "__main__":
    # Mock data for testing
    data = {
        'rsi': np.random.uniform(0, 100, 100),
        'target_return_1d': np.random.normal(0, 1, 100)
    }
    df = pd.DataFrame(data)
    
    engine = GAEngine(df)
    best_rules, _ = engine.run(generations=5)
    
    print("\nTop Rules:")
    for rule in best_rules:
        print(f"{engine.decode_rule(rule)} => Fitness: {rule.fitness.values[0]:.2f}")
