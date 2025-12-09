import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  Alert,
  RefreshControl,
  Platform,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import axios from 'axios';
import { API_BASE_URL } from '../constants/config';
import LoadingView from './common/LoadingView';

const { width } = Dimensions.get('window');

interface DashboardStats {
  total_fridge_items: number;
  total_pantry_items: number;
  fresh_items: number;
  spoiled_items: number;
  expiring_soon: number;
  favorite_recipes_count: number;
}

interface FridgeItemSummary {
  id: string;
  name: string;
  category?: string;
  quantity?: number;
  unit?: string;
  freshness_status?: string;
  detected_date: string;
}

interface ExpiringItem {
  id: string;
  name: string;
  type: string;
  expiry_date: string;
  days_until_expiry: number;
}

const DashboardScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const [stats, setStats] = useState<DashboardStats>({
    total_fridge_items: 0,
    total_pantry_items: 0,
    fresh_items: 0,
    spoiled_items: 0,
    expiring_soon: 0,
    favorite_recipes_count: 0,
  });
  const [recentScans, setRecentScans] = useState<FridgeItemSummary[]>([]);
  const [expiringItems, setExpiringItems] = useState<ExpiringItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [refreshing, setRefreshing] = useState(false);

  const getFreshnessColor = (status?: string) => {
    switch ((status || '').toLowerCase()) {
      case 'fresh':
        return '#4CAF50';
      case 'spoiled':
        return '#E53935';
      default:
        return '#95A5A6';
    }
  };

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return '';

    const diffMs = Date.now() - date.getTime();
    const diffMinutes = Math.max(0, Math.round(diffMs / 60000));

    if (diffMinutes < 1) return 'just now';
    if (diffMinutes < 60) return `${diffMinutes} min${diffMinutes === 1 ? '' : 's'} ago`;

    const diffHours = Math.round(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours} hr${diffHours === 1 ? '' : 's'} ago`;

    const diffDays = Math.round(diffHours / 24);
    return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
  };

  const statCards = [
    {
      key: 'fridge-items',
      title: 'Fridge Items',
      value: 0,
      icon: 'cube',
      color: '#4CAF50',
      onPress: () => navigation.navigate('Scanner'),
    },
    {
      key: 'pantry-items',
      title: 'Pantry Items',
      value: stats.total_pantry_items,
      icon: 'basket',
      color: '#2196F3',
      onPress: () => navigation.navigate('Pantry'),
    },
    {
      key: 'spoiled-items',
      title: 'Spoiled Items',
      value: stats.spoiled_items,
      icon: 'warning',
      color: '#F44336',
    },
    {
      key: 'expiring-soon',
      title: 'Expiring Soon',
      value: stats.expiring_soon,
      icon: 'timer',
      color: '#FFB300',
      onPress: () => navigation.navigate('Pantry', { showExpiringFilter: '1week' }),
    },
    {
      key: 'favorites',
      title: 'Favorite Recipes',
      value: stats.favorite_recipes_count,
      icon: 'heart',
      color: '#E91E63',
      onPress: () => navigation.navigate('Recipes'),
    },
  ];

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsResponse, recentResponse, expiringResponse] = await Promise.all([
        axios.get(`${API_BASE_URL}/dashboard/stats`),
        axios.get(`${API_BASE_URL}/dashboard/recent-scans`),
        axios.get(`${API_BASE_URL}/dashboard/expiring-items`),
      ]);
      setStats(statsResponse.data);
      setRecentScans(recentResponse.data || []);
      setExpiringItems(expiringResponse.data || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      Alert.alert('Dashboard', 'Unable to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchDashboardData();
    setRefreshing(false);
  }, [fetchDashboardData]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const StatCard: React.FC<{
    title: string;
    value: number;
    icon: string;
    color: string;
    onPress?: () => void;
  }> = ({ title, value, icon, color, onPress }) => (
    <TouchableOpacity
      style={[styles.statCard, { borderLeftColor: color }]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.statCardContent}>
        <View style={styles.statCardLeft}>
          <Text style={styles.statValue}>{value}</Text>
          <Text style={styles.statTitle}>{title}</Text>
        </View>
        <View style={[styles.statIcon, { backgroundColor: color }]}>
          <Ionicons name={icon as any} size={24} color="white" />
        </View>
      </View>
    </TouchableOpacity>
  );

  const QuickActionButton: React.FC<{
    title: string;
    icon: string;
    color: string;
    onPress: () => void;
  }> = ({ title, icon, color, onPress }) => (
    <TouchableOpacity
      style={[styles.quickActionButton, { backgroundColor: color }]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <Ionicons name={icon as any} size={28} color="white" />
      <Text style={styles.quickActionText}>{title}</Text>
    </TouchableOpacity>
  );

  if (loading) {
    return <LoadingView message="Loading dashboard..." />;
  }

  return (
    <SafeAreaView style={styles.safeContainer} edges={['top']}>
      <ScrollView
        style={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>FridgeScan Dashboard</Text>
          <Text style={styles.headerSubtitle}>Smart food management at your fingertips</Text>
        </View>

      {/* Quick Actions */}
      <View style={styles.quickActionsSection}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.quickActionsGrid}>
          <QuickActionButton
            title="Scan Fridge"
            icon="camera"
            color="#4CAF50"
            onPress={() => navigation.navigate('Scanner')}
          />
          <QuickActionButton
            title="Add Pantry Item"
            icon="add-circle"
            color="#2196F3"
            onPress={() => navigation.navigate('AddPantryItem')}
          />
          <QuickActionButton
            title="Browse Recipes"
            icon="book"
            color="#FF9800"
            onPress={() => navigation.navigate('Recipes')}
          />
          <QuickActionButton
            title="View Nutrition"
            icon="nutrition"
            color="#9C27B0"
            onPress={() => navigation.navigate('Nutrition')}
          />
        </View>
      </View>

      {/* Stats Grid */}
      <View style={styles.statsGrid}>
        {statCards.map(card => (
          <StatCard
            key={card.key}
            title={card.title}
            value={card.value}
            icon={card.icon}
            color={card.color}
            onPress={card.onPress}
          />
        ))}
      </View>

      {/* Expiring Items */}
      <View style={styles.expiringSection}>
        <Text style={styles.sectionTitle}>Expiring Soon</Text>
        <View style={styles.expiringList}>
          {expiringItems.length === 0 ? (
            <Text style={styles.emptyListText}>No pantry items expiring in the next 7 days.</Text>
          ) : (
            expiringItems.slice(0, 5).map(item => (
              <View key={item.id} style={styles.expiringItem}>
                <View style={styles.expiringBadge}>
                  <Ionicons name="timer" size={18} color="#FFB300" />
                </View>
                <View style={styles.expiringContent}>
                  <Text style={styles.expiringName}>{item.name}</Text>
                  <Text style={styles.expiringMeta}>
                    {item.days_until_expiry === 0
                      ? 'Expires today'
                      : `${item.days_until_expiry} day${item.days_until_expiry === 1 ? '' : 's'} left`}
                  </Text>
                </View>
              </View>
            ))
          )}
        </View>
      </View>

      {/* Recent Activity */}
      <View style={styles.recentActivitySection}>
        <Text style={styles.sectionTitle}>Recent Activity</Text>
        <View style={styles.activityList}>
          {recentScans.length === 0 ? (
            <Text style={styles.emptyListText}>No recent scans yet.</Text>
          ) : (
            recentScans.map(item => (
              <View key={item.id} style={styles.activityItem}>
                <View style={[styles.activityIcon, { backgroundColor: getFreshnessColor(item.freshness_status) }]}>
                  <Ionicons name="camera" size={16} color="#FFFFFF" />
                </View>
                <View style={styles.activityContent}>
                  <Text style={styles.activityTitle}>{item.name}</Text>
                  <Text style={styles.activityMeta}>
                    {item.quantity ? `${item.quantity} ${item.unit || ''} • ` : ''}
                    {formatRelativeTime(item.detected_date)}
                  </Text>
                </View>
              </View>
            ))
          )}
        </View>
      </View>
    </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeContainer: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    backgroundColor: '#FFFFFF',
    padding: 20,
    paddingTop: 20,
    paddingBottom: 25,
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
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 15,
    paddingTop: 5,
    gap: 15,
    justifyContent: 'space-between',
  },
  statCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 18,
    flexBasis: (width - 60) / 2,
    flexGrow: 1,
    minWidth: (width - 60) / 2,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statCardContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statCardLeft: {
    flex: 1,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 5,
  },
  statTitle: {
    fontSize: 14,
    color: '#7F8C8D',
    fontWeight: '500',
  },
  statIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quickActionsSection: {
    padding: 15,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 15,
  },
  quickActionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 15,
  },
  quickActionButton: {
    borderRadius: 12,
    padding: 20,
    width: (width - 45) / 2,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  quickActionText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    marginTop: 8,
  },
  recentActivitySection: {
    padding: 15,
  },
  activityList: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    gap: 12,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  activityIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 15,
  },
  activityContent: {
    flex: 1,
  },
  activityTitle: {
    fontSize: 16,
    color: '#2C3E50',
    fontWeight: '500',
  },
  activityMeta: {
    fontSize: 12,
    color: '#7F8C8D',
    marginTop: 2,
  },
  alertSection: {
    padding: 15,
    paddingBottom: 30,
  },
  alertCard: {
    backgroundColor: '#FFF3E0',
    borderRadius: 12,
    padding: 15,
    flexDirection: 'row',
    alignItems: 'center',
    borderLeftWidth: 4,
    borderLeftColor: '#F44336',
  },
  alertContent: {
    flex: 1,
    marginLeft: 15,
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#F44336',
    marginBottom: 5,
  },
  alertText: {
    fontSize: 14,
    color: '#666',
  },
  expiringSection: {
    padding: 15,
  },
  expiringList: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    gap: 12,
  },
  expiringItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  expiringBadge: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#FFF3E0',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  expiringContent: {
    flex: 1,
  },
  expiringName: {
    fontSize: 15,
    color: '#2C3E50',
    fontWeight: '500',
  },
  expiringMeta: {
    fontSize: 12,
    color: '#7F8C8D',
    marginTop: 2,
  },
  emptyListText: {
    fontSize: 14,
    color: '#7F8C8D',
    textAlign: 'center',
  },
});

export default DashboardScreen;
