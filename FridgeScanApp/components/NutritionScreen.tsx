import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Dimensions,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { API_BASE_URL } from '../constants/config';
import LoadingView from './common/LoadingView';
import { PieChart } from 'react-native-chart-kit';

const { width } = Dimensions.get('window');

interface NutritionData {
  calories: number;
  protein: number;
  carbs: number;
  fats: number;
  fiber?: number;
  sugar?: number;
  sodium?: number;
}

interface RecipeNutrition {
  log_id: string;
  recipe_id: string;
  recipe_name: string;
  nutrition_per_serving: NutritionData;
  total_servings: number;
  daily_values: {
    calories: number;
    protein: number;
    carbs: number;
    fats: number;
  };
  logged_at: string;
}

const DAILY_TARGETS = {
  calories: 2000,
  protein: 50,
  carbs: 275,
  fats: 70,
};

const computeDailyValues = (nutrition: NutritionData) => ({
  calories: Math.min(100, Math.round((nutrition.calories / DAILY_TARGETS.calories) * 100)),
  protein: Math.min(100, Math.round((nutrition.protein / DAILY_TARGETS.protein) * 100)),
  carbs: Math.min(100, Math.round((nutrition.carbs / DAILY_TARGETS.carbs) * 100)),
  fats: Math.min(100, Math.round((nutrition.fats / DAILY_TARGETS.fats) * 100)),
});

const NutritionScreen: React.FC = () => {
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeNutrition | null>(null);
  const [nutritionHistory, setNutritionHistory] = useState<RecipeNutrition[]>([]);
  const [dailySummary, setDailySummary] = useState<NutritionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<'today' | 'week' | 'month'>('today');

  const periods = [
    { key: 'today', label: 'Today', icon: 'calendar' },
    { key: 'week', label: 'This Week', icon: 'calendar-outline' },
    { key: 'month', label: 'This Month', icon: 'calendar-sharp' },
  ];

  const fetchNutritionData = async () => {
    try {
      const [historyResp, summaryResp] = await Promise.all([
        axios.get(`${API_BASE_URL}/nutrition/logs`),
        axios.get(`${API_BASE_URL}/nutrition/daily-summary`),
      ]);

      const logs: RecipeNutrition[] = (historyResp.data?.logs || []).map((log: any, index: number) => {
        const perServing: NutritionData = {
          calories: log.per_serving?.calories ?? 0,
          protein: log.per_serving?.protein ?? 0,
          carbs: log.per_serving?.carbs ?? 0,
          fats: log.per_serving?.fats ?? 0,
          fiber: log.per_serving?.fiber ?? 0,
          sugar: log.per_serving?.sugar ?? 0,
          sodium: log.per_serving?.sodium ?? 0,
        };

        return {
          log_id: log.id ?? `${Date.now()}-${index}`,
          recipe_id: log.recipe_id ?? 'unknown',
          recipe_name: log.recipe_name ?? 'Logged Meal',
          nutrition_per_serving: perServing,
          total_servings: log.servings ?? 1,
          daily_values: computeDailyValues(perServing),
          logged_at: log.logged_at ?? new Date().toISOString(),
        };
      });

      setNutritionHistory(logs);
      setSelectedRecipe(logs.length > 0 ? logs[0] : null);

      const totals = summaryResp.data?.totals;
      if (totals) {
        setDailySummary({
          calories: totals.calories ?? 0,
          protein: totals.protein ?? 0,
          carbs: totals.carbs ?? 0,
          fats: totals.fats ?? 0,
          fiber: totals.fiber ?? 0,
          sugar: totals.sugar ?? 0,
          sodium: totals.sodium ?? 0,
        });
      } else {
        setDailySummary(null);
      }
    } catch (error) {
      console.error('Error fetching nutrition data:', error);
      Alert.alert('Nutrition', 'Unable to load nutrition data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNutritionData();
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchNutritionData();
    setRefreshing(false);
  }, []);

  const getMacroColor = (macro: string) => {
    switch (macro) {
      case 'protein': return '#4CAF50';
      case 'carbs': return '#2196F3';
      case 'fat': return '#FF9800';
      default: return '#9E9E9E';
    }
  };

  const getMacroIcon = (macro: string) => {
    switch (macro) {
      case 'protein': return 'fitness';
      case 'carbs': return 'nutrition';
      case 'fat': return 'flame';
      default: return 'help-circle';
    }
  };

  const getProgressColor = (percentage: number) => {
    if (percentage >= 80) return '#4CAF50';
    if (percentage >= 60) return '#FF9800';
    return '#F44336';
  };

  const MacroCard: React.FC<{ macro: string; value: number; dailyValue: number; unit: string }> = 
    ({ macro, value, dailyValue, unit }) => (
      <View style={styles.macroCard}>
        <View style={styles.macroHeader}>
          <View style={[styles.macroIcon, { backgroundColor: getMacroColor(macro) }]}>
            <Ionicons name={getMacroIcon(macro) as any} size={20} color="white" />
          </View>
          <View style={styles.macroInfo}>
            <Text style={styles.macroName}>{macro.toUpperCase()}</Text>
            <Text style={styles.macroValue}>{value}g</Text>
          </View>
          <Text style={styles.macroUnit}>{unit}</Text>
        </View>
        
        <View style={styles.progressContainer}>
          <View style={styles.progressBar}>
            <View 
              style={[
                styles.progressFill, 
                { 
                  width: `${Math.min(dailyValue, 100)}%`,
                  backgroundColor: getProgressColor(dailyValue)
                }
              ]} 
            />
          </View>
          <Text style={styles.progressText}>{dailyValue}% of daily value</Text>
        </View>
      </View>
    );

  const NutritionChart: React.FC<{ nutrition: NutritionData }> = ({ nutrition }) => {
    const chartData = [
      {
        name: 'Protein',
        population: nutrition.protein * 4, // 4 calories per gram
        color: '#4CAF50',
        legendFontColor: '#7F8C8D',
        legendFontSize: 12,
      },
      {
        name: 'Carbs',
        population: nutrition.carbs * 4, // 4 calories per gram
        color: '#2196F3',
        legendFontColor: '#7F8C8D',
        legendFontSize: 12,
      },
      {
        name: 'Fat',
        population: nutrition.fats * 9, // 9 calories per gram
        color: '#FF9800',
        legendFontColor: '#7F8C8D',
        legendFontSize: 12,
      },
    ];

    return (
      <View style={styles.chartContainer}>
        <Text style={styles.chartTitle}>Calorie Breakdown</Text>
        <PieChart
          data={chartData}
          width={width - 80}
          height={220}
          chartConfig={{
            color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
          }}
          accessor="population"
          backgroundColor="transparent"
          paddingLeft="15"
          center={[10, 10]}
          absolute
        />
      </View>
    );
  };

  const NutritionDetail: React.FC<{ label: string; value: number; unit: string }> = 
    ({ label, value, unit }) => (
      <View style={styles.nutritionDetail}>
        <Text style={styles.nutritionLabel}>{label}</Text>
        <Text style={styles.nutritionValue}>{value}{unit}</Text>
      </View>
    );

  const PeriodSelector: React.FC = () => (
    <View style={styles.periodSelector}>
      {periods.map(period => (
        <TouchableOpacity
          key={period.key}
          style={[
            styles.periodButton,
            selectedPeriod === period.key && styles.periodButtonActive
          ]}
          onPress={() => setSelectedPeriod(period.key as any)}
        >
          <Ionicons 
            name={period.icon as any} 
            size={16} 
            color={selectedPeriod === period.key ? '#FFFFFF' : '#7F8C8D'} 
          />
          <Text style={[
            styles.periodButtonText,
            selectedPeriod === period.key && styles.periodButtonTextActive
          ]}>
            {period.label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );

  if (loading) {
    return <LoadingView message="Loading nutrition data..." />;
  }

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Nutrition Analysis</Text>
        <Text style={styles.headerSubtitle}>Track your nutritional intake and goals</Text>
      </View>

      {/* Period Selector */}
      <View style={styles.periodSection}>
        <PeriodSelector />
      </View>

      {/* Selected Recipe */}
      {selectedRecipe && (
        <View style={styles.recipeSection}>
          <View style={styles.recipeHeader}>
            <Text style={styles.recipeTitle}>{selectedRecipe.recipe_name}</Text>
            <Text style={styles.recipeServings}>
              {selectedRecipe.total_servings} servings
            </Text>
          </View>

          {/* Calorie Overview */}
          <View style={styles.calorieOverview}>
            <View style={styles.calorieMain}>
              <Text style={styles.calorieValue}>{selectedRecipe.nutrition_per_serving.calories}</Text>
              <Text style={styles.calorieUnit}>calories</Text>
            </View>
            <View style={styles.calorieDetails}>
              <Text style={styles.caloriePerServing}>per serving</Text>
              <Text style={styles.calorieTotal}>
                {selectedRecipe.nutrition_per_serving.calories * selectedRecipe.total_servings} total
              </Text>
            </View>
          </View>

          {/* Macro Cards */}
          <View style={styles.macrosSection}>
            <Text style={styles.sectionTitle}>Macronutrients</Text>
            <View style={styles.macrosGrid}>
              <MacroCard
                macro="protein"
                value={selectedRecipe.nutrition_per_serving.protein}
                dailyValue={selectedRecipe.daily_values.protein}
                unit="g"
              />
              <MacroCard
                macro="carbs"
                value={selectedRecipe.nutrition_per_serving.carbs}
                dailyValue={selectedRecipe.daily_values.carbs}
                unit="g"
              />
              <MacroCard
                macro="fats"
                value={selectedRecipe.nutrition_per_serving.fats}
                dailyValue={selectedRecipe.daily_values.fats}
                unit="g"
              />
            </View>
          </View>

          {/* Nutrition Chart */}
          <NutritionChart nutrition={selectedRecipe.nutrition_per_serving} />

          {/* Detailed Nutrition */}
          <View style={styles.detailedNutrition}>
            <Text style={styles.sectionTitle}>Detailed Nutrition</Text>
            <View style={styles.nutritionGrid}>
              <NutritionDetail
                label="Fiber"
                value={selectedRecipe.nutrition_per_serving.fiber ?? 0}
                unit="g"
              />
              <NutritionDetail
                label="Sugar"
                value={selectedRecipe.nutrition_per_serving.sugar ?? 0}
                unit="g"
              />
              <NutritionDetail
                label="Sodium"
                value={selectedRecipe.nutrition_per_serving.sodium ?? 0}
                unit="mg"
              />
              <NutritionDetail
                label="Servings Logged"
                value={selectedRecipe.total_servings}
                unit={selectedRecipe.total_servings === 1 ? 'serving' : 'servings'}
              />
            </View>
          </View>
        </View>
      )}
      {!selectedRecipe && (
        <View style={styles.emptyState}>
          <Ionicons name="restaurant-outline" size={42} color="#9E9E9E" />
          <Text style={styles.emptyStateTitle}>No nutrition logs yet</Text>
          <Text style={styles.emptyStateSubtitle}>
            Log a meal from your recipes to view detailed nutrition insights.
          </Text>
        </View>
      )}

      {/* Daily Goals */}
      <View style={styles.goalsSection}>
        <Text style={styles.sectionTitle}>Daily Nutrition Goals</Text>
        <View style={styles.goalsCard}>
          <View style={styles.goalItem}>
            <Text style={styles.goalLabel}>Calories</Text>
            <View style={styles.goalProgress}>
              <View style={styles.goalBar}>
                <View
                  style={[
                    styles.goalFill,
                    {
                      width: `${Math.min(
                        100,
                        ((dailySummary?.calories ?? 0) / DAILY_TARGETS.calories) * 100,
                      )}%`,
                      backgroundColor: '#4CAF50',
                    },
                  ]}
                />
              </View>
              <Text style={styles.goalText}>
                {Math.round(dailySummary?.calories ?? 0)} / {DAILY_TARGETS.calories}
              </Text>
            </View>
          </View>
          
          <View style={styles.goalItem}>
            <Text style={styles.goalLabel}>Protein</Text>
            <View style={styles.goalProgress}>
              <View style={styles.goalBar}>
                <View
                  style={[
                    styles.goalFill,
                    {
                      width: `${Math.min(
                        100,
                        ((dailySummary?.protein ?? 0) / DAILY_TARGETS.protein) * 100,
                      )}%`,
                      backgroundColor: '#4CAF50',
                    },
                  ]}
                />
              </View>
              <Text style={styles.goalText}>
                {Math.round(dailySummary?.protein ?? 0)}g / {DAILY_TARGETS.protein}g
              </Text>
            </View>
          </View>
          
          <View style={styles.goalItem}>
            <Text style={styles.goalLabel}>Carbs</Text>
            <View style={styles.goalProgress}>
              <View style={styles.goalBar}>
                <View
                  style={[
                    styles.goalFill,
                    {
                      width: `${Math.min(
                        100,
                        ((dailySummary?.carbs ?? 0) / DAILY_TARGETS.carbs) * 100,
                      )}%`,
                      backgroundColor: '#FF9800',
                    },
                  ]}
                />
              </View>
              <Text style={styles.goalText}>
                {Math.round(dailySummary?.carbs ?? 0)}g / {DAILY_TARGETS.carbs}g
              </Text>
            </View>
          </View>
          
          <View style={styles.goalItem}>
            <Text style={styles.goalLabel}>Fat</Text>
            <View style={styles.goalProgress}>
              <View style={styles.goalBar}>
                <View
                  style={[
                    styles.goalFill,
                    {
                      width: `${Math.min(
                        100,
                        ((dailySummary?.fats ?? 0) / DAILY_TARGETS.fats) * 100,
                      )}%`,
                      backgroundColor: '#FF9800',
                    },
                  ]}
                />
              </View>
              <Text style={styles.goalText}>
                {Math.round(dailySummary?.fats ?? 0)}g / {DAILY_TARGETS.fats}g
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* Tips Section */}
      <View style={styles.tipsSection}>
        <Text style={styles.sectionTitle}>💡 Nutrition Tips</Text>
        <View style={styles.tipsList}>
          <View style={styles.tipItem}>
            <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
            <Text style={styles.tipText}>Increase protein intake with lean meats and legumes</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
            <Text style={styles.tipText}>Include more fiber-rich vegetables and whole grains</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
            <Text style={styles.tipText}>Limit processed foods to reduce sodium intake</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
            <Text style={styles.tipText}>Stay hydrated with 8+ glasses of water daily</Text>
          </View>
        </View>
      </View>

    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    backgroundColor: '#FFFFFF',
    padding: 20,
    paddingTop: 60,
    paddingBottom: 30,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 5,
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#7F8C8D',
  },
  periodSection: {
    padding: 20,
  },
  periodSelector: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  periodButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 8,
    gap: 5,
  },
  periodButtonActive: {
    backgroundColor: '#2196F3',
  },
  periodButtonText: {
    fontSize: 14,
    color: '#7F8C8D',
    fontWeight: '500',
  },
  periodButtonTextActive: {
    color: '#FFFFFF',
  },
  recipeSection: {
    padding: 20,
  },
  recipeHeader: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  recipeTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 5,
  },
  recipeServings: {
    fontSize: 16,
    color: '#7F8C8D',
  },
  calorieOverview: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  calorieMain: {
    alignItems: 'center',
    marginRight: 30,
  },
  calorieValue: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#2C3E50',
  },
  calorieUnit: {
    fontSize: 16,
    color: '#7F8C8D',
    marginTop: 5,
  },
  calorieDetails: {
    flex: 1,
  },
  caloriePerServing: {
    fontSize: 16,
    color: '#7F8C8D',
    marginBottom: 5,
  },
  calorieTotal: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2C3E50',
  },
  macrosSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 15,
  },
  macrosGrid: {
    gap: 15,
  },
  macroCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  macroHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  macroIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 15,
  },
  macroInfo: {
    flex: 1,
  },
  macroName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2C3E50',
    marginBottom: 2,
  },
  macroValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2C3E50',
  },
  macroUnit: {
    fontSize: 14,
    color: '#7F8C8D',
  },
  progressContainer: {
    gap: 5,
  },
  progressBar: {
    height: 8,
    backgroundColor: '#E0E0E0',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  progressText: {
    fontSize: 12,
    color: '#7F8C8D',
    textAlign: 'right',
  },
  chartContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  chartTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 15,
  },
  detailedNutrition: {
    marginBottom: 20,
  },
  nutritionGrid: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  nutritionDetail: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  nutritionLabel: {
    fontSize: 16,
    color: '#7F8C8D',
  },
  nutritionValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2C3E50',
  },
  goalsSection: {
    padding: 20,
  },
  goalsCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  goalItem: {
    marginBottom: 20,
  },
  goalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2C3E50',
    marginBottom: 8,
  },
  goalProgress: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 15,
  },
  goalBar: {
    flex: 1,
    height: 8,
    backgroundColor: '#E0E0E0',
    borderRadius: 4,
    overflow: 'hidden',
  },
  goalFill: {
    height: '100%',
    borderRadius: 4,
  },
  goalText: {
    fontSize: 14,
    color: '#7F8C8D',
    minWidth: 80,
    textAlign: 'right',
  },
  tipsSection: {
    padding: 20,
  },
  tipsList: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
    gap: 12,
  },
  tipText: {
    flex: 1,
    fontSize: 14,
    color: '#7F8C8D',
    lineHeight: 20,
  },
  actionSection: {
    flexDirection: 'row',
    padding: 20,
    gap: 15,
    paddingBottom: 40,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 15,
    borderRadius: 12,
    gap: 8,
  },
  recipeButton: {
    backgroundColor: '#4CAF50',
  },
  goalsButton: {
    backgroundColor: '#2196F3',
  },
  actionButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
    gap: 12,
  },
  emptyStateTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#626567',
  },
  emptyStateSubtitle: {
    fontSize: 14,
    color: '#909497',
    textAlign: 'center',
    paddingHorizontal: 32,
    lineHeight: 20,
  },
});

export default NutritionScreen;
