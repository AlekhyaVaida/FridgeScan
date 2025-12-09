import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  FlatList,
  Image,
  Dimensions,
  RefreshControl,
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { API_BASE_URL } from '../constants/config';
import LoadingView from './common/LoadingView';

const { width } = Dimensions.get('window');

interface Recipe {
  id: string;
  title: string;
  image_url?: string;
  ready_in_minutes?: number;
  servings?: number;
  difficulty?: 'easy' | 'medium' | 'hard';
  cuisine?: string;
  ingredients: string[];
  instructions?: string[];
  match_percentage?: number;
  missing_ingredients?: string[];
  nutrition_info?: {
    calories: number;
    protein: number;
    carbs: number;
    fat: number;
  };
  is_favorite: boolean;
}

interface RecipeFilters {
  difficulty: string;
  max_time: number;
  min_servings: number;
}

const RecipesScreen: React.FC = () => {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [filteredRecipes, setFilteredRecipes] = useState<Recipe[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [showRecipeModal, setShowRecipeModal] = useState(false);
  const [filters, setFilters] = useState<RecipeFilters>({
    difficulty: 'all',
    max_time: 999, // High value to show all recipes by default
    min_servings: 1,
  });

  const difficulties = ['all', 'easy', 'medium', 'hard'];
  const timeOptions = [15, 30, 45, 60, 90, 120, 999]; // Added 999 for "All" option

  const mapIngredientLines = (value: any): string[] => {
    if (!value) return [];
    if (Array.isArray(value)) {
      return value
        .map((item: any) => {
          if (typeof item === 'string') return item;
          if (item?.display) return item.display;
          if (item?.name) {
            const measure = item?.measure ?? item?.amount ?? '';
            return `${measure ?? ''} ${item.name}`.trim();
          }
          return '';
        })
        .filter(Boolean);
    }
    if (typeof value === 'string') {
      return value
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean);
    }
    return [];
  };

  const mapInstructions = (value: any): string[] => {
    if (!value) return [];
    
    let lines: string[] = [];
    
    if (Array.isArray(value)) {
      lines = value.map((item: any) => String(item).trim()).filter(Boolean);
    } else if (typeof value === 'string') {
      lines = value.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    } else {
      return [];
    }
    
    // Process lines to filter out "STEP X" headers and clean instructions
    const processed: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Check if this line is just a step header (e.g., "STEP 1", "Step 1:", "STEP 1:", etc.)
      // Match patterns like: "STEP 1", "STEP 1:", "Step 1", "Step 1:", etc.
      const isStepHeader = /^STEP\s+\d+[\.\):]?\s*$/i.test(line);
      
      if (isStepHeader) {
        // Skip this line (it's just a header)
        // The next line should be the actual instruction
        continue;
      }
      
      // Regular instruction line - remove step numbers and "STEP X" patterns if present
      let cleaned = line
        .replace(/^STEP\s+\d+[\.\):]?\s*/i, '') // Remove "STEP 1:" at start
        .replace(/^(Step\s*)?\d+[\.\):]\s*/i, '') // Remove "1. " or "Step 1:" at start
        .trim();
      
      // Only add if it's not empty and not another step header
      if (cleaned && !/^STEP\s+\d+[\.\):]?\s*$/i.test(cleaned)) {
        processed.push(cleaned);
      }
    }
    
    return processed;
  };

  const mapApiRecipe = (recipe: any, index: number): Recipe => {
    // Handle ingredients - can be array of strings, array of objects, or extendedIngredients
    let ingredients: string[] = [];
    if (recipe.ingredients) {
      ingredients = mapIngredientLines(recipe.ingredients);
    } else if (recipe.extendedIngredients) {
      // Handle extendedIngredients format from full recipe details
      ingredients = recipe.extendedIngredients.map((ing: any) => {
        if (typeof ing === 'string') return ing;
        const amount = ing.amount ?? ing.measure ?? '';
        const unit = ing.unit ?? '';
        const name = ing.name ?? ing.originalName ?? '';
        return `${amount} ${unit} ${name}`.trim();
      }).filter(Boolean);
    } else if (recipe.used_ingredients) {
      ingredients = mapIngredientLines(recipe.used_ingredients);
    }

    const matchPercentageRaw = recipe.match_percentage ?? recipe.matchPercentage ?? 0;
    const matchPercentage = typeof matchPercentageRaw === 'number'
      ? Math.round(matchPercentageRaw)
      : Math.round(parseFloat(matchPercentageRaw) || 0);

    // Handle instructions - can be array of strings or a single string
    let instructions: string[] = [];
    if (recipe.instructions) {
      instructions = mapInstructions(recipe.instructions);
    } else if (recipe.analyzedInstructions) {
      instructions = mapInstructions(recipe.analyzedInstructions);
    }

    return {
      id: recipe.id?.toString() ?? recipe.external_id ?? `${Date.now()}-${index}`,
      title: recipe.title ?? 'Untitled Recipe',
      image_url: recipe.image ?? recipe.image_url ?? undefined,
      ready_in_minutes: recipe.ready_in_minutes ?? recipe.readyInMinutes ?? recipe.cooking_time ?? recipe.time ?? undefined,
      servings: recipe.servings ?? recipe.yield ?? undefined,
      difficulty: 'easy',
      cuisine:
        recipe.cuisine ??
        recipe.area ??
        (Array.isArray(recipe.cuisines) ? recipe.cuisines[0] : undefined),
      ingredients,
      instructions,
      match_percentage: matchPercentage,
      missing_ingredients: Array.isArray(recipe.missing_ingredients)
        ? recipe.missing_ingredients.map((ing: any) => {
            if (typeof ing === 'string') return ing;
            return ing.name ?? ing.originalName ?? String(ing);
          }).filter(Boolean)
        : [],
      is_favorite: recipe.is_favorite ?? false,
      nutrition_info: recipe.nutrition ? {
        calories: recipe.nutrition.nutrients?.find((n: any) => n.name === 'Calories')?.amount ?? 0,
        protein: recipe.nutrition.nutrients?.find((n: any) => n.name === 'Protein')?.amount ?? 0,
        carbs: recipe.nutrition.nutrients?.find((n: any) => n.name === 'Carbohydrates')?.amount ?? 0,
        fat: recipe.nutrition.nutrients?.find((n: any) => n.name === 'Fat')?.amount ?? 0,
      } : undefined,
    };
  };

  const fetchRecipes = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/recipes/suggestions`);
      const mappedRecipes: Recipe[] = (response.data || [])
        .map((recipe: any, index: number) => mapApiRecipe(recipe, index))
        .sort((a: Recipe, b: Recipe) => (b.match_percentage ?? 0) - (a.match_percentage ?? 0));

      setRecipes(mappedRecipes);
      setFilteredRecipes(mappedRecipes);
    } catch (error) {
      console.error('Error fetching recipes:', error);
      Alert.alert('Recipes', 'Unable to load recipe suggestions. Showing previous results.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecipes();
  }, [fetchRecipes]);

  const applyFilters = useCallback(
    (list: Recipe[], query: string, filterState: RecipeFilters) => {
      let filtered = [...list];

      const trimmedQuery = query.trim().toLowerCase();
      if (trimmedQuery) {
        filtered = filtered.filter(recipe =>
          recipe.title.toLowerCase().includes(trimmedQuery)
        );
      }

      if (filterState.difficulty !== 'all') {
        filtered = filtered.filter(recipe => recipe.difficulty === filterState.difficulty);
      }

      filtered = filtered.filter(recipe => {
        if (recipe.ready_in_minutes == null) {
          return true;
        }
        return recipe.ready_in_minutes <= filterState.max_time;
      });

      filtered = filtered.filter(recipe => {
        if (recipe.servings == null) {
          return true;
        }
        return recipe.servings >= filterState.min_servings;
      });

      return filtered.sort((a, b) => (b.match_percentage ?? 0) - (a.match_percentage ?? 0));
    },
    []
  );

  const calculateMatchPercentage = useCallback((recipeIngredients: string[], availableIngredients: string[]): number => {
    if (!recipeIngredients.length) return 0;
    
    const availableLower = availableIngredients.map(ing => ing.toLowerCase());
    const matched = recipeIngredients.filter(ing => {
      const ingLower = ing.toLowerCase();
      return availableLower.some(avail => 
        avail.includes(ingLower) || ingLower.includes(avail)
      );
    });
    
    return Math.round((matched.length / recipeIngredients.length) * 100);
  }, []);

  const handleSearch = useCallback(async () => {
    const term = searchQuery.trim();
    if (!term) {
      await fetchRecipes();
      return;
    }

    try {
      setLoading(true);
      
      // Get available ingredients to calculate match percentage
      const [searchResponse, pantryResponse, fridgeResponse] = await Promise.all([
        axios.get(`${API_BASE_URL}/recipes/search/by-name`, {
          params: { query: term },
        }),
        axios.get(`${API_BASE_URL}/pantry/items`).catch(() => ({ data: [] })),
        axios.get(`${API_BASE_URL}/fridge/items`).catch(() => ({ data: [] })),
      ]);

      // Get available ingredients
      const pantryItems = pantryResponse.data || [];
      const fridgeItems = fridgeResponse.data || [];
      const availableIngredients = [
        ...pantryItems.map((item: any) => item.name),
        ...fridgeItems.map((item: any) => item.name),
      ].filter(Boolean);

      // Map recipes and calculate match percentage
      const mappedRecipes: Recipe[] = (searchResponse.data || []).map((recipe: any, index: number) => {
        const mapped = mapApiRecipe(recipe, index);
        
        // Calculate match percentage if not present
        if (!mapped.match_percentage && mapped.ingredients.length > 0) {
          const matchPct = calculateMatchPercentage(mapped.ingredients, availableIngredients);
          mapped.match_percentage = matchPct;
          
          // Calculate missing ingredients
          const recipeIngLower = mapped.ingredients.map(ing => ing.toLowerCase());
          const availableLower = availableIngredients.map(ing => ing.toLowerCase());
          mapped.missing_ingredients = mapped.ingredients.filter(ing => {
            const ingLower = ing.toLowerCase();
            return !availableLower.some(avail => 
              avail.includes(ingLower) || ingLower.includes(avail)
            );
          });
        }
        
        return mapped;
      }).sort((a: Recipe, b: Recipe) => (b.match_percentage ?? 0) - (a.match_percentage ?? 0));
      
      setRecipes(mappedRecipes);
    } catch (error) {
      console.error('Error searching recipes:', error);
      Alert.alert('Recipes', 'Unable to search recipes right now. Keeping previous results.');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, fetchRecipes, calculateMatchPercentage]);

  const handleClearSearch = useCallback(async () => {
    setSearchQuery('');
    await fetchRecipes();
  }, [fetchRecipes]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    if (searchQuery.trim()) {
      await handleSearch();
    } else {
      await fetchRecipes();
    }
    setRefreshing(false);
  }, [fetchRecipes, handleSearch, searchQuery]);

  useEffect(() => {
    setFilteredRecipes(applyFilters(recipes, searchQuery, filters));
  }, [recipes, searchQuery, filters, applyFilters]);


  const toggleFavorite = useCallback(async (recipeId: string) => {
    try {
      const recipe = recipes.find(r => r.id === recipeId);
      if (!recipe) return;

      if (recipe.is_favorite) {
        await axios.delete(`${API_BASE_URL}/recipes/favorites/${recipeId}`);
      } else {
        await axios.post(`${API_BASE_URL}/recipes/favorites`, { recipe_id: recipeId });
      }

      setRecipes(prev =>
        prev.map(r => (r.id === recipeId ? { ...r, is_favorite: !r.is_favorite } : r))
      );
    } catch (error) {
      console.error('Error toggling favorite:', error);
      Alert.alert('Recipes', 'Unable to update favorites right now.');
    }
  }, [recipes]);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '#4CAF50';
      case 'medium': return '#FF9800';
      case 'hard': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  const getMatchColor = (percentage: number) => {
    if (percentage >= 80) return '#4CAF50';
    if (percentage >= 60) return '#FF9800';
    return '#F44336';
  };

  const handleRecipePress = useCallback(async (recipe: Recipe) => {
    try {
      setShowRecipeModal(true);
      setLoading(true);
      
      // Fetch full recipe details
      const response = await axios.get(`${API_BASE_URL}/recipes/${recipe.id}`);
      const fullRecipe = mapApiRecipe(response.data, 0);
      
      setSelectedRecipe(fullRecipe);
    } catch (error) {
      console.error('Error fetching recipe details:', error);
      // Fallback to using the summary data if detail fetch fails
      setSelectedRecipe(recipe);
      Alert.alert('Recipe', 'Unable to load full recipe details. Showing summary.');
    } finally {
      setLoading(false);
    }
  }, []);

  const RecipeCard: React.FC<{ recipe: Recipe }> = ({ recipe }) => (
    <TouchableOpacity
      style={styles.recipeCard}
      onPress={() => handleRecipePress(recipe)}
      activeOpacity={0.7}
    >
      <View style={styles.recipeImageContainer}>
        <Image source={{ uri: recipe.image_url }} style={styles.recipeImage} />
        <TouchableOpacity
          style={styles.favoriteButton}
          onPress={() => toggleFavorite(recipe.id)}
        >
          <Ionicons
            name={recipe.is_favorite ? 'heart' : 'heart-outline'}
            size={24}
            color={recipe.is_favorite ? '#F44336' : '#FFFFFF'}
          />
        </TouchableOpacity>
        <View style={styles.matchBadge}>
          <Text style={[styles.matchText, { color: getMatchColor(recipe.match_percentage ?? 0) }]}>
            {recipe.match_percentage ?? 0}% match
          </Text>
        </View>
      </View>

      <View style={styles.recipeContent}>
        <Text style={styles.recipeTitle}>{recipe.title}</Text>
        
        <View style={styles.recipeMeta}>
          {recipe.ready_in_minutes != null && (
            <View style={styles.metaItem}>
              <Ionicons name="time" size={16} color="#7F8C8D" />
              <Text style={styles.metaText}>
                {recipe.ready_in_minutes} min
              </Text>
            </View>
          )}
          {recipe.servings != null && (
            <View style={styles.metaItem}>
              <Ionicons name="people" size={16} color="#7F8C8D" />
              <Text style={styles.metaText}>
                {recipe.servings} servings
              </Text>
            </View>
          )}
          <View style={styles.metaItem}>
            <Ionicons name="restaurant" size={16} color="#7F8C8D" />
            <Text style={styles.metaText}>{recipe.match_percentage ?? 0}% match</Text>
          </View>
        </View>

        {recipe.missing_ingredients && recipe.missing_ingredients.length > 0 && (
          <View style={styles.missingIngredients}>
            <Text style={styles.missingText}>
              Missing: {recipe.missing_ingredients.join(', ')}
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  const FilterSection: React.FC = () => {
    if (!showFilters) return null;
    
    return (
      <View style={styles.filterContainer}>
        <View style={styles.filterHeader}>
          <Text style={styles.filterTitle}>Filter Recipes</Text>
          <TouchableOpacity onPress={() => setShowFilters(false)}>
            <Ionicons name="close" size={24} color="#7F8C8D" />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.filterContent}>
          <View style={styles.filterSection}>
            <Text style={styles.filterSectionTitle}>Difficulty</Text>
            <View style={styles.filterRow}>
              {difficulties.map(difficulty => (
                <TouchableOpacity
                  key={difficulty}
                  style={[
                    styles.filterChip,
                    filters.difficulty === difficulty && styles.filterChipActive
                  ]}
                  onPress={() => setFilters(prev => ({ ...prev, difficulty }))}
                >
                  <Text style={[
                    styles.filterChipText,
                    filters.difficulty === difficulty && styles.filterChipTextActive
                  ]}>
                    {difficulty}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.filterSection}>
            <Text style={styles.filterSectionTitle}>Max Cooking Time</Text>
            <View style={styles.filterRow}>
              {timeOptions.map(time => (
                <TouchableOpacity
                  key={time}
                  style={[
                    styles.filterChip,
                    filters.max_time === time && styles.filterChipActive
                  ]}
                  onPress={() => setFilters(prev => ({ ...prev, max_time: time }))}
                >
                  <Text style={[
                    styles.filterChipText,
                    filters.max_time === time && styles.filterChipTextActive
                  ]}>
                    {time === 999 ? 'All' : `${time} min`}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </ScrollView>

        <View style={styles.filterFooter}>
          <TouchableOpacity
            style={styles.clearFiltersButton}
            onPress={() => {
              setFilters({
                difficulty: 'all',
                max_time: 999, // High value to show all recipes
                min_servings: 1,
              });
              setShowFilters(false);
            }}
          >
            <Text style={styles.clearFiltersText}>Clear All</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.applyFiltersButton}
            onPress={() => setShowFilters(false)}
          >
            <Text style={styles.applyFiltersText}>Apply Filters</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const RecipeModal: React.FC = React.memo(() => (
    <Modal
      visible={showRecipeModal}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={() => setShowRecipeModal(false)}
    >
      {loading && !selectedRecipe ? (
        <View style={styles.recipeModalContainer}>
          <View style={styles.recipeModalHeader}>
            <Text style={styles.recipeModalTitle}>Loading Recipe...</Text>
            <TouchableOpacity onPress={() => {
              setShowRecipeModal(false);
              setLoading(false);
            }}>
              <Ionicons name="close" size={24} color="#7F8C8D" />
            </TouchableOpacity>
          </View>
          <View style={styles.recipeModalContent}>
            <LoadingView message="Loading recipe details..." />
          </View>
        </View>
      ) : selectedRecipe ? (
        <View style={styles.recipeModalContainer}>
          <View style={styles.recipeModalHeader}>
            <Text style={styles.recipeModalTitle}>{selectedRecipe.title}</Text>
            <TouchableOpacity onPress={() => setShowRecipeModal(false)}>
              <Ionicons name="close" size={24} color="#7F8C8D" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.recipeModalContent}>
            {selectedRecipe.image_url && (
              <Image source={{ uri: selectedRecipe.image_url }} style={styles.recipeModalImage} />
            )}
            
            <View style={styles.recipeModalMeta}>
              {selectedRecipe.ready_in_minutes != null && (
                <View style={styles.recipeModalMetaItem}>
                  <Ionicons name="time" size={20} color="#7F8C8D" />
                  <Text style={styles.recipeModalMetaText}>{selectedRecipe.ready_in_minutes} minutes</Text>
                </View>
              )}
              {selectedRecipe.servings != null && (
                <View style={styles.recipeModalMetaItem}>
                  <Ionicons name="people" size={20} color="#7F8C8D" />
                  <Text style={styles.recipeModalMetaText}>{selectedRecipe.servings} servings</Text>
                </View>
              )}
            </View>

            {selectedRecipe.ingredients && selectedRecipe.ingredients.length > 0 ? (
              <View style={styles.recipeModalSection}>
                <Text style={styles.recipeModalSectionTitle}>Ingredients</Text>
                {selectedRecipe.ingredients.map((ingredient, index) => (
                  <Text key={index} style={styles.ingredientItem}>• {ingredient}</Text>
                ))}
              </View>
            ) : (
              <View style={styles.recipeModalSection}>
                <Text style={styles.recipeModalSectionTitle}>Ingredients</Text>
                <Text style={styles.emptyText}>No ingredients available</Text>
              </View>
            )}

            {selectedRecipe.missing_ingredients && selectedRecipe.missing_ingredients.length > 0 && (
              <View style={styles.recipeModalSection}>
                <Text style={styles.recipeModalSectionTitle}>Missing Ingredients</Text>
                <Text style={styles.missingIngredientsText}>
                  {selectedRecipe.missing_ingredients.join(', ')}
                </Text>
              </View>
            )}

            {selectedRecipe.instructions && selectedRecipe.instructions.length > 0 ? (
              <View style={styles.recipeModalSection}>
                <Text style={styles.recipeModalSectionTitle}>Instructions</Text>
                {selectedRecipe.instructions.map((instruction, index) => (
                  <View key={index} style={styles.instructionItem}>
                    <Text style={styles.instructionNumber}>{index + 1}</Text>
                    <Text style={styles.instructionText}>{instruction}</Text>
                  </View>
                ))}
              </View>
            ) : (
              <View style={styles.recipeModalSection}>
                <Text style={styles.recipeModalSectionTitle}>Instructions</Text>
                <Text style={styles.emptyText}>No instructions available</Text>
              </View>
            )}

            {selectedRecipe.nutrition_info && (
              <View style={styles.recipeModalSection}>
                <Text style={styles.recipeModalSectionTitle}>Nutrition (per serving)</Text>
                <View style={styles.nutritionGrid}>
                  <View style={styles.nutritionItem}>
                    <Text style={styles.nutritionValue}>{selectedRecipe.nutrition_info.calories}</Text>
                    <Text style={styles.nutritionLabel}>Calories</Text>
                  </View>
                  <View style={styles.nutritionItem}>
                    <Text style={styles.nutritionValue}>{selectedRecipe.nutrition_info.protein}g</Text>
                    <Text style={styles.nutritionLabel}>Protein</Text>
                  </View>
                  <View style={styles.nutritionItem}>
                    <Text style={styles.nutritionValue}>{selectedRecipe.nutrition_info.carbs}g</Text>
                    <Text style={styles.nutritionLabel}>Carbs</Text>
                  </View>
                  <View style={styles.nutritionItem}>
                    <Text style={styles.nutritionValue}>{selectedRecipe.nutrition_info.fat}g</Text>
                    <Text style={styles.nutritionLabel}>Fat</Text>
                  </View>
                </View>
              </View>
            )}
          </ScrollView>

          <View style={styles.recipeModalFooter} />
        </View>
      ) : (
        <View style={styles.recipeModalContainer}>
          <View style={styles.recipeModalHeader}>
            <Text style={styles.recipeModalTitle}>No Recipe Selected</Text>
            <TouchableOpacity onPress={() => setShowRecipeModal(false)}>
              <Ionicons name="close" size={24} color="#7F8C8D" />
            </TouchableOpacity>
          </View>
          <View style={styles.recipeModalContent}>
            <Text style={styles.emptyText}>Please select a recipe to view details.</Text>
          </View>
        </View>
      )}
    </Modal>
  ));

  if (loading) {
    return <LoadingView message="Loading recipes..." />;
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Recipe Suggestions</Text>
        <Text style={styles.headerSubtitle}>Discover recipes based on your ingredients</Text>
      </View>

      {/* Search and Filter */}
      <View style={styles.searchSection}>
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color="#7F8C8D" />
          <TextInput
            style={styles.searchInput}
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search recipes..."
            placeholderTextColor="#7F8C8D"
            returnKeyType="search"
            onSubmitEditing={() => handleSearch()}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={handleClearSearch} style={styles.searchClearButton}>
              <Ionicons name="close-circle" size={20} color="#95A5A6" />
            </TouchableOpacity>
          )}
        </View>
        <TouchableOpacity style={styles.searchActionButton} onPress={handleSearch}>
          <Ionicons name="arrow-forward" size={24} color="white" />
        </TouchableOpacity>
        <TouchableOpacity style={styles.filterButton} onPress={() => setShowFilters(!showFilters)}>
          <Ionicons name="options" size={24} color="white" />
        </TouchableOpacity>
      </View>

      {/* Filter Section - Inline */}
      <FilterSection />

      {/* Results Count */}
      {!showFilters && (
        <View style={styles.resultsHeader}>
          <Text style={styles.resultsText}>
            {filteredRecipes.length} recipe{filteredRecipes.length !== 1 ? 's' : ''} found
          </Text>
        </View>
      )}

      {/* Recipes List */}
      <FlatList
        data={filteredRecipes}
        renderItem={({ item }) => <RecipeCard recipe={item} />}
        keyExtractor={(item) => item.id}
        style={styles.recipesList}
        contentContainerStyle={styles.recipesListContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        showsVerticalScrollIndicator={false}
      />

      {/* Recipe Detail Modal */}
      <RecipeModal />
    </View>
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
  searchSection: {
    flexDirection: 'row',
    padding: 20,
    gap: 15,
  },
  searchContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 15,
    paddingVertical: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    color: '#2C3E50',
    marginLeft: 10,
  },
  searchClearButton: {
    padding: 4,
  },
  searchActionButton: {
    backgroundColor: '#4CAF50',
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  filterButton: {
    backgroundColor: '#FF9800',
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  resultsHeader: {
    paddingHorizontal: 20,
    marginBottom: 10,
  },
  resultsText: {
    fontSize: 14,
    color: '#7F8C8D',
  },
  recipesList: {
    flex: 1,
  },
  recipesListContent: {
    padding: 20,
    gap: 20,
  },
  recipeCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
  },
  recipeImageContainer: {
    position: 'relative',
    height: 200,
  },
  recipeImage: {
    width: '100%',
    height: '100%',
  },
  favoriteButton: {
    position: 'absolute',
    top: 15,
    right: 15,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: 20,
    padding: 8,
  },
  matchBadge: {
    position: 'absolute',
    bottom: 15,
    left: 15,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  matchText: {
    fontSize: 14,
    fontWeight: '600',
  },
  recipeContent: {
    padding: 20,
  },
  recipeTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 12,
  },
  recipeMeta: {
    flexDirection: 'row',
    gap: 15,
    marginBottom: 12,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  metaText: {
    fontSize: 14,
    color: '#7F8C8D',
  },
  difficultyDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  cuisineContainer: {
    alignSelf: 'flex-start',
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
    marginBottom: 12,
  },
  cuisineText: {
    fontSize: 12,
    color: '#1976D2',
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  missingIngredients: {
    backgroundColor: '#FFF3E0',
    padding: 10,
    borderRadius: 8,
  },
  missingText: {
    fontSize: 14,
    color: '#F57C00',
    fontStyle: 'italic',
  },
  // Filter Modal styles
  filterContainer: {
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 2,
    borderBottomColor: '#E0E0E0',
    maxHeight: '70%',
  },
  filterHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 15,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  filterTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2C3E50',
  },
  filterContent: {
    padding: 20,
    maxHeight: 500,
  },
  filterSection: {
    marginBottom: 30,
  },
  filterSectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2C3E50',
    marginBottom: 15,
  },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  filterChipActive: {
    backgroundColor: '#2196F3',
  },
  filterChipText: {
    fontSize: 14,
    color: '#7F8C8D',
    fontWeight: '500',
    textTransform: 'capitalize',
  },
  filterChipTextActive: {
    color: '#FFFFFF',
  },
  filterFooter: {
    flexDirection: 'row',
    padding: 20,
    gap: 15,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  clearFiltersButton: {
    flex: 1,
    padding: 15,
    borderRadius: 12,
    backgroundColor: '#E0E0E0',
    alignItems: 'center',
  },
  clearFiltersText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#7F8C8D',
  },
  applyFiltersButton: {
    flex: 1,
    padding: 15,
    borderRadius: 12,
    backgroundColor: '#2196F3',
    alignItems: 'center',
  },
  applyFiltersText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  // Recipe Modal styles
  recipeModalContainer: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  recipeModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  recipeModalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2C3E50',
    flex: 1,
    marginRight: 20,
  },
  recipeModalContent: {
    flex: 1,
  },
  recipeModalImage: {
    width: '100%',
    height: 250,
  },
  recipeModalMeta: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 20,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  recipeModalMetaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  recipeModalMetaText: {
    fontSize: 16,
    color: '#7F8C8D',
  },
  recipeModalSection: {
    backgroundColor: '#FFFFFF',
    padding: 20,
    marginTop: 10,
  },
  recipeModalSectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 15,
  },
  ingredientItem: {
    fontSize: 16,
    color: '#7F8C8D',
    marginBottom: 8,
    lineHeight: 24,
  },
  emptyText: {
    fontSize: 16,
    color: '#9E9E9E',
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 20,
  },
  missingIngredientsText: {
    fontSize: 16,
    color: '#F57C00',
    fontStyle: 'italic',
  },
  instructionItem: {
    flexDirection: 'row',
    marginBottom: 15,
    gap: 15,
  },
  instructionNumber: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#2196F3',
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
    lineHeight: 30,
  },
  instructionText: {
    flex: 1,
    fontSize: 16,
    color: '#7F8C8D',
    lineHeight: 24,
  },
  nutritionGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  nutritionItem: {
    alignItems: 'center',
  },
  nutritionValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
  },
  nutritionLabel: {
    fontSize: 14,
    color: '#7F8C8D',
  },
  recipeModalFooter: {
    padding: 20,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  recipeModalButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 15,
    borderRadius: 12,
    gap: 8,
  },
  cookButton: {
    backgroundColor: '#4CAF50',
  },
  recipeModalButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});

export default RecipesScreen;
