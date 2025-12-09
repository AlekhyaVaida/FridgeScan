import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import ScannerScreen from './ScannerScreen';
import PantryScreen from './PantryScreen';
import RecipesScreen from './RecipesScreen';
import NutritionScreen from './NutritionScreen';

const Tab = createBottomTabNavigator();

const TabNavigator: React.FC = () => {
  return (
    <Tab.Navigator
      initialRouteName="Pantry"
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: string;

          switch (route.name) {
            case 'Scanner':
              iconName = focused ? 'camera' : 'camera-outline';
              break;
            case 'Pantry':
              iconName = focused ? 'storefront' : 'storefront-outline';
              break;
            case 'Recipes':
              iconName = focused ? 'book' : 'book-outline';
              break;
            case 'Nutrition':
              iconName = focused ? 'nutrition' : 'nutrition-outline';
              break;
            default:
              iconName = 'help-circle-outline';
          }

          return <Ionicons name={iconName as any} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: '#7F8C8D',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopWidth: 1,
          borderTopColor: '#E0E0E0',
          paddingTop: 5,
          paddingBottom: Platform.OS === 'ios' ? 30 : 10,
          height: Platform.OS === 'ios' ? 85 : 60,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.1,
          shadowRadius: 4,
          elevation: 5,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
          marginTop: 2,
          marginBottom: Platform.OS === 'ios' ? 5 : 0,
        },
        headerShown: false,
      })}
    >
      <Tab.Screen 
        name="Scanner" 
        component={ScannerScreen}
        options={{
          tabBarLabel: 'Scanner',
        }}
      />
      <Tab.Screen 
        name="Pantry" 
        component={PantryScreen}
        options={{
          tabBarLabel: 'My Pantry',
        }}
      />
      <Tab.Screen 
        name="Recipes" 
        component={RecipesScreen}
        options={{
          tabBarLabel: 'Recipes',
        }}
      />
      <Tab.Screen 
        name="Nutrition" 
        component={NutritionScreen}
        options={{
          tabBarLabel: 'Nutrition',
        }}
      />
    </Tab.Navigator>
  );
};

export default TabNavigator;
