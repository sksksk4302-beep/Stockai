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
        self.features = [col for col in df.columns if col not in ['date', 'ticker', 'name', 'target_return_1d']]
        self.toolbox = base.Toolbox()
        self._setup_toolbox()

    def _setup_toolbox(self):
        # Gene: [Feature_Index, Operator(0: <, 1: >), Threshold]
        self.toolbox.register("attr_feat", random.randint, 0, len(self.features)-1)
        self.toolbox.register("attr_op", random.randint, 0, 1)
        self.toolbox.register("attr_thres", random.uniform, -2.0, 2.0) # Normalized threshold
        
        # Condition: A single rule part
        self.toolbox.register("condition", tools.initCycle, list,
                             (self.toolbox.attr_feat, self.toolbox.attr_op, self.toolbox.attr_thres), n=1)
        
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
                individual[cond_idx][0] = random.randint(0, len(self.features)-1)
            elif gene_idx == 1: # Operator
                individual[cond_idx][1] = 1 - individual[cond_idx][1]
            else: # Threshold
                individual[cond_idx][2] += random.gauss(0, 0.5)
                
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
