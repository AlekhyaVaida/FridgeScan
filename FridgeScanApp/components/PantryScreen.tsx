import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput, Alert, FlatList, Dimensions, RefreshControl } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRoute, useNavigation, useFocusEffect } from '@react-navigation/native';
import axios from 'axios';

import { API_BASE_URL } from '../constants/config';
import LoadingView from './common/LoadingView';

const { width } = Dimensions.get('window');

interface PantryItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  expiry_date: string | null;
  added_date: string;
}

const PantryScreen: React.FC = () => {
  const route = useRoute();
  const navigation = useNavigation<any>();

  const [pantryItems, setPantryItems] = useState<PantryItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<PantryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedExpiryFilter, setSelectedExpiryFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);

  const categories = useMemo(
    () => [
      { key: 'all', label: 'All Items', icon: 'grid', emoji: '📦' },
      { key: 'dairy', label: 'Dairy', icon: 'water', emoji: '🥛' },
      { key: 'vegetables', label: 'Vegetables', icon: 'leaf', emoji: '🥬' },
      { key: 'fruits', label: 'Fruits', icon: 'nutrition', emoji: '🍎' },
      { key: 'meat', label: 'Meat', icon: 'restaurant', emoji: '🥩' },
      { key: 'grains', label: 'Grains', icon: 'cafe', emoji: '🌾' },
      { key: 'spices', label: 'Spices', icon: 'flame', emoji: '🌶️' },
      { key: 'beverages', label: 'Beverages', icon: 'wine', emoji: '🥤' },
    ],
    []
  );

  const expiryFilters = useMemo(() => {
    const filters: Array<{
      key: string;
      label: string;
      minDays: number;
      maxDays: number | null;
    }> = [
      { key: '2days', label: '< 2 days', minDays: 0, maxDays: 2 },
      { key: '1week', label: '< 1 week', minDays: 0, maxDays: 7 },
      { key: '2weeks', label: '< 2 weeks', minDays: 0, maxDays: 14 },
      { key: '1month', label: '≥ 1 month', minDays: 30, maxDays: null },
    ];
    return filters;
  }, []);

  const fetchPantryItems = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/pantry/items`);
      const items: PantryItem[] = response.data ?? [];
      // Sort by added_date descending (newest first)
      const sortedItems = [...items].sort((a, b) => {
        const dateA = new Date(a.added_date).getTime();
        const dateB = new Date(b.added_date).getTime();
        return dateB - dateA; // Descending order (newest first)
      });
      setPantryItems(sortedItems);
      setFilteredItems(sortedItems);
    } catch (error: any) {
      console.error('Error fetching pantry items:', error?.response?.data || error);
      Alert.alert('Pantry', 'Unable to load pantry items. Please try again.');
      setPantryItems([]);
      setFilteredItems([]);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      let isMounted = true;

      const load = async () => {
        setLoading(true);
        await fetchPantryItems();
        if (isMounted) {
          setLoading(false);
        }
      };

      load();

      return () => {
        isMounted = false;
      };
    }, [fetchPantryItems])
  );

  useEffect(() => {
    const params = route.params as any;
    const filterKey = params?.showExpiringFilter as string | undefined;
    if (filterKey) {
      setSelectedExpiryFilter(filterKey);
      navigation.setParams({ showExpiringFilter: undefined });
    }
  }, [(route.params as any)?.showExpiringFilter]);

  useEffect(() => {
    filterItems();
  }, [searchQuery, selectedCategory, selectedExpiryFilter, pantryItems]);

  // Get matching pantry items for search dropdown
  const getMatchingItems = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const query = searchQuery.toLowerCase();
    const matches = pantryItems
      .filter((item) => item.name.toLowerCase().includes(query))
      .slice(0, 10); // Limit to 10 results
    return matches;
  }, [searchQuery, pantryItems]);

  const filterItems = useCallback(() => {
    let filtered = pantryItems;

    if (selectedCategory !== 'all') {
      filtered = filtered.filter((item) => item.category === selectedCategory);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((item) => item.name.toLowerCase().includes(query));
    }

    if (selectedExpiryFilter) {
      const filter = expiryFilters.find((f) => f.key === selectedExpiryFilter);
      if (filter) {
        const now = new Date();
        now.setHours(0, 0, 0, 0);
        const MS_PER_DAY = 1000 * 60 * 60 * 24;

        filtered = filtered.filter((item) => {
          if (!item.expiry_date) return false;
          const expiryDate = new Date(item.expiry_date);
          if (Number.isNaN(expiryDate.getTime())) return false;
          const expiryMidnight = new Date(expiryDate);
          expiryMidnight.setHours(0, 0, 0, 0);

          const diffDays = Math.floor((expiryMidnight.getTime() - now.getTime()) / MS_PER_DAY);
          if (diffDays < 0) return false;
          if (typeof filter.minDays === 'number' && diffDays < filter.minDays) {
            return false;
          }
          if (typeof filter.maxDays === 'number' && diffDays > filter.maxDays) {
            return false;
          }
          return true;
        });
      }
    }

    // Sort by added_date descending (newest first) to maintain order
    const sorted = [...filtered].sort((a, b) => {
      const dateA = new Date(a.added_date).getTime();
      const dateB = new Date(b.added_date).getTime();
      return dateB - dateA; // Descending order (newest first)
    });

    setFilteredItems(sorted);
  }, [expiryFilters, pantryItems, searchQuery, selectedCategory, selectedExpiryFilter]);

  const toggleCategory = useCallback((categoryKey: string) => {
    setSelectedCategory((prev) => {
      if (prev === categoryKey) {
        return 'all';
      }
      return categoryKey;
    });
  }, []);

  const toggleExpiryFilter = useCallback((filterKey: string | null) => {
    setSelectedExpiryFilter((prev) => {
      if (prev === filterKey) {
        return null;
      }
      return filterKey;
    });
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchPantryItems();
    setRefreshing(false);
  }, [fetchPantryItems]);

  const deletePantryItem = useCallback((id: string) => {
    Alert.alert(
      'Delete Item',
      'Are you sure you want to delete this item?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await axios.delete(`${API_BASE_URL}/pantry/items/${id}`);
              setPantryItems((prev) => prev.filter((item) => item.id !== id));
            } catch (error) {
              console.error('Error deleting pantry item:', error);
              setPantryItems((prev) => prev.filter((item) => item.id !== id));
            }
          },
        },
      ]
    );
  }, []);

  const formatExpiryDate = (value: string | null) => {
    if (!value) {
      return 'No expiry date';
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return parsed.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const handleAddPress = useCallback(() => {
    navigation.navigate('AddPantryItem', {
      initialCategory: selectedCategory === 'all' ? undefined : selectedCategory,
    });
  }, [navigation, selectedCategory]);


  const ExpiryFilter = useMemo(
    () => () => (
      <View style={styles.expiryFilter}>
        <Text style={styles.filterSectionTitle}>Expiry Filters</Text>
        <ScrollView 
          horizontal 
          showsHorizontalScrollIndicator={false}
          style={styles.expiryFilterScrollView}
          contentContainerStyle={styles.expiryFilterRow}
        >
          {expiryFilters.map((filter) => (
            <TouchableOpacity
              key={filter.key}
              style={[
                styles.expiryFilterButton,
                selectedExpiryFilter === filter.key && styles.expiryFilterButtonActive,
              ]}
              onPress={() => toggleExpiryFilter(filter.key)}
            >
              <Ionicons
                name="time"
                size={14}
                color={selectedExpiryFilter === filter.key ? '#FFFFFF' : '#F44336'}
              />
              <Text
                style={[
                  styles.expiryFilterButtonText,
                  selectedExpiryFilter === filter.key && styles.expiryFilterButtonTextActive,
                ]}
              >
                {filter.label}
              </Text>
            </TouchableOpacity>
          ))}
          {selectedExpiryFilter && (
            <TouchableOpacity
              style={styles.clearExpiryFilterButton}
              onPress={() => toggleExpiryFilter(null)}
            >
              <Ionicons name="close-circle" size={14} color="#7F8C8D" />
              <Text style={styles.clearExpiryFilterText}>Clear</Text>
            </TouchableOpacity>
          )}
        </ScrollView>
      </View>
    ),
    [expiryFilters, selectedExpiryFilter, toggleExpiryFilter]
  );

  if (loading) {
    return <LoadingView message="Loading pantry items..." />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Pantry Management</Text>
        <Text style={styles.headerSubtitle}>Manage your pantry inventory</Text>
      </View>

      <View style={styles.searchSection}>
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color="#7F8C8D" />
          <TextInput
            style={styles.searchInput}
            value={searchQuery}
            onChangeText={(text) => {
              setSearchQuery(text);
              setShowSearchDropdown(text.length > 0);
              setShowCategoryDropdown(false);
            }}
            onFocus={() => {
              if (searchQuery.length > 0) {
                setShowSearchDropdown(true);
              }
            }}
            onBlur={() => {
              // Delay hiding dropdown to allow item selection
              setTimeout(() => setShowSearchDropdown(false), 200);
            }}
            placeholder="Search pantry items..."
            placeholderTextColor="#7F8C8D"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity
              onPress={() => {
                setSearchQuery('');
                setShowCategoryDropdown(false);
                setShowSearchDropdown(false);
              }}
            >
              <Ionicons name="close-circle" size={20} color="#7F8C8D" />
            </TouchableOpacity>
          )}
        </View>
        <TouchableOpacity style={styles.addButton} onPress={handleAddPress}>
          <Ionicons name="add" size={24} color="white" />
        </TouchableOpacity>
      </View>

      {/* Search Dropdown - Shows matching pantry items */}
      {showSearchDropdown && getMatchingItems.length > 0 && (
        <View style={styles.searchDropdown}>
          {getMatchingItems.map((item, index) => (
            <TouchableOpacity
              key={item.id}
              style={[
                styles.searchDropdownItem,
                index === getMatchingItems.length - 1 && styles.searchDropdownItemLast,
              ]}
              onPress={() => {
                setSearchQuery(item.name);
                setShowSearchDropdown(false);
              }}
            >
              <Ionicons name="search" size={16} color="#7F8C8D" />
              <Text style={styles.searchDropdownText}>{item.name}</Text>
              <Text style={styles.searchDropdownCategory}>{item.category}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Category Dropdown - Shows when searching */}
      {showCategoryDropdown && (
        <View style={styles.categoryDropdown}>
          <Text style={styles.dropdownTitle}>Filter by Category</Text>
          <View style={styles.categoryDropdownGrid}>
            {categories.map((category) => (
              <TouchableOpacity
                key={category.key}
                style={[
                  styles.categoryDropdownItem,
                  selectedCategory === category.key && styles.categoryDropdownItemActive,
                ]}
                onPress={() => {
                  setSelectedCategory(category.key);
                  setShowCategoryDropdown(false);
                }}
              >
              <Text style={styles.categoryDropdownEmoji}>{category.emoji}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Show selected category filter when active */}
      {selectedCategory !== 'all' && !showCategoryDropdown && (
        <View style={styles.activeFilterBadge}>
          <View style={styles.activeFilterContent}>
            <Text style={styles.activeFilterEmoji}>
              {categories.find(c => c.key === selectedCategory)?.emoji || '📦'}
            </Text>
            <Text style={styles.activeFilterText}>
              {categories.find(c => c.key === selectedCategory)?.label || 'Category'}
            </Text>
            <TouchableOpacity
              onPress={() => setSelectedCategory('all')}
              style={styles.clearCategoryButton}
            >
              <Ionicons name="close-circle" size={18} color="#7F8C8D" />
            </TouchableOpacity>
          </View>
        </View>
      )}

      <ExpiryFilter />

      <FlatList
        data={filteredItems}
        renderItem={({ item }) => (
          <View style={styles.itemCard}>
            <View style={styles.itemHeader}>
              <View style={styles.itemInfo}>
                <Text style={styles.itemName}>{item.name}</Text>
                <Text style={styles.itemDetails}>
                  {item.quantity} {item.unit} • {item.category}
                </Text>
              </View>
              <TouchableOpacity style={styles.deleteButton} onPress={() => deletePantryItem(item.id)}>
                <Text style={styles.deleteText}>Delete</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.itemFooter}>
              <Text style={styles.expiryText}>{formatExpiryDate(item.expiry_date)}</Text>
            </View>
          </View>
        )}
        keyExtractor={(item) => item.id}
        style={styles.itemsList}
        contentContainerStyle={styles.itemsListContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <Text style={styles.emptyListText}>No pantry items found. Add your first item!</Text>
        }
      />
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
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    color: '#2C3E50',
    marginLeft: 10,
  },
  addButton: {
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
  categoryDropdown: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 20,
    marginBottom: 15,
    borderRadius: 12,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  dropdownTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#7F8C8D',
    marginBottom: 12,
  },
  categoryDropdownGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  categoryDropdownItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#F5F5F5',
    minWidth: 50,
  },
  categoryDropdownItemActive: {
    backgroundColor: '#2196F3',
  },
  categoryDropdownEmoji: {
    fontSize: 24,
  },
  categoryDropdownText: {
    fontSize: 13,
    color: '#7F8C8D',
    fontWeight: '500',
  },
  categoryDropdownTextActive: {
    color: '#FFFFFF',
  },
  activeFilterBadge: {
    marginHorizontal: 20,
    marginBottom: 15,
  },
  activeFilterContent: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 8,
    alignSelf: 'flex-start',
  },
  activeFilterEmoji: {
    fontSize: 18,
  },
  activeFilterText: {
    fontSize: 13,
    color: '#2196F3',
    fontWeight: '600',
  },
  clearCategoryButton: {
    marginLeft: 4,
  },
  expiryFilter: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  filterSectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#7F8C8D',
    marginBottom: 10,
  },
  expiryFilterScrollView: {
    flexGrow: 0,
  },
  expiryFilterRow: {
    flexDirection: 'row',
    gap: 8,
    paddingRight: 10,
  },
  expiryFilterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#F44336',
    gap: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  expiryFilterButtonActive: {
    backgroundColor: '#F44336',
    borderColor: '#F44336',
  },
  expiryFilterButtonText: {
    fontSize: 11,
    fontWeight: '500',
    color: '#F44336',
  },
  expiryFilterButtonTextActive: {
    color: '#FFFFFF',
  },
  clearExpiryFilterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E0E0E0',
    gap: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  clearExpiryFilterText: {
    fontSize: 11,
    fontWeight: '500',
    color: '#7F8C8D',
  },
  itemsList: {
    flex: 1,
  },
  itemsListContent: {
    padding: 20,
    gap: 15,
  },
  itemCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2C3E50',
    textTransform: 'capitalize',
    marginBottom: 5,
  },
  itemDetails: {
    fontSize: 14,
    color: '#7F8C8D',
  },
  deleteButton: {
    padding: 5,
  },
  deleteText: {
    fontSize: 14,
    color: '#F44336',
    fontWeight: '600',
  },
  itemFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  expiryText: {
    fontSize: 12,
    color: '#7F8C8D',
  },
  emptyListText: {
    fontSize: 14,
    color: '#7F8C8D',
    textAlign: 'center',
  },
  searchDropdown: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 20,
    marginTop: -10,
    marginBottom: 15,
    borderRadius: 12,
    maxHeight: 200,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    overflow: 'hidden',
  },
  searchDropdownItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
    gap: 10,
  },
  searchDropdownItemLast: {
    borderBottomWidth: 0,
  },
  searchDropdownText: {
    flex: 1,
    fontSize: 16,
    color: '#2C3E50',
    fontWeight: '500',
  },
  searchDropdownCategory: {
    fontSize: 12,
    color: '#7F8C8D',
    textTransform: 'capitalize',
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
  },
});

export default PantryScreen;
