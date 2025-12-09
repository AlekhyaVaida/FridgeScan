import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import axios from 'axios';

import { API_BASE_URL } from '../constants/config';

type Navigation = ReturnType<typeof useNavigation<any>>;

interface RouteParams {
  initialCategory?: string;
}

const categories = [
  { key: 'dairy', label: 'Dairy' },
  { key: 'vegetables', label: 'Vegetables' },
  { key: 'fruits', label: 'Fruits' },
  { key: 'meat', label: 'Meat' },
  { key: 'grains', label: 'Grains' },
  { key: 'spices', label: 'Spices' },
  { key: 'beverages', label: 'Beverages' },
];

const units = ['pieces', 'kg', 'g', 'lbs', 'oz', 'ml', 'l', 'cups', 'tbsp', 'tsp'];

const AddPantryItemScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const route = useRoute();
  const params = route.params as RouteParams | undefined;

  const defaultCategory = useMemo(() => {
    if (!params?.initialCategory || params.initialCategory === 'all') {
      return 'dairy';
    }
    return params.initialCategory;
  }, [params?.initialCategory]);

  const [name, setName] = useState('');
  const [category, setCategory] = useState(defaultCategory);
  const [quantity, setQuantity] = useState('1');
  const [unit, setUnit] = useState('pieces');
  const [expiryMonth, setExpiryMonth] = useState('');
  const [expiryDay, setExpiryDay] = useState('');
  const [expiryYear, setExpiryYear] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim()) {
      Alert.alert('Add Pantry Item', 'Please enter an item name.');
      return;
    }

    const parsedQuantity = Number(quantity);
    if (Number.isNaN(parsedQuantity) || parsedQuantity <= 0) {
      Alert.alert('Add Pantry Item', 'Please enter a valid quantity greater than zero.');
      return;
    }

    const payload: Record<string, any> = {
      name: name.trim(),
      category,
      quantity: parsedQuantity,
      unit,
    };

    const hasPartialExpiry =
      expiryMonth.trim() !== '' || expiryDay.trim() !== '' || expiryYear.trim() !== '';
    if (hasPartialExpiry) {
      if (!expiryMonth.trim() || !expiryDay.trim() || !expiryYear.trim()) {
        Alert.alert('Add Pantry Item', 'Please complete the expiry date (month, day, and year).');
        return;
      }

      const month = expiryMonth.padStart(2, '0');
      const day = expiryDay.padStart(2, '0');
      const year = expiryYear.length === 2 ? `20${expiryYear}` : expiryYear;

      const isoString = `${year}-${month}-${day}T00:00:00`;
      const parsedDate = new Date(isoString);
      if (Number.isNaN(parsedDate.getTime())) {
        Alert.alert('Add Pantry Item', 'Please enter a valid expiry date.');
        return;
      }
      payload.expiry_date = isoString;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API_BASE_URL}/pantry/items`, payload);

      Alert.alert('Success', 'Pantry item added successfully.', [
        {
          text: 'OK',
          onPress: () => {
            setName('');
            setCategory(defaultCategory);
            setQuantity('1');
            setUnit('pieces');
            setExpiryMonth('');
            setExpiryDay('');
            setExpiryYear('');
            setNotes('');
            navigation.navigate('MainTabs', {
              screen: 'Pantry',
              params: { refreshTimestamp: Date.now() },
            });
          },
        },
      ]);
    } catch (error: any) {
      console.error('Error adding pantry item:', error?.response?.data || error);
      Alert.alert(
        'Unable to add item',
        'Please try again. If the problem persists, confirm the backend is reachable.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const disabled = submitting;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
          accessibilityLabel="Go back"
        >
          <Ionicons name="chevron-back" size={24} color="#2C3E50" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Add Pantry Item</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.contentContainer}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Item Name *</Text>
          <TextInput
            value={name}
            onChangeText={setName}
            placeholder="Enter item name"
            style={styles.textInput}
            autoFocus
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Category</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {categories.map((item) => (
              <TouchableOpacity
                key={item.key}
                style={[
                  styles.pillButton,
                  category === item.key && styles.pillButtonActive,
                ]}
                onPress={() => setCategory(item.key)}
              >
                <Text
                  style={[
                    styles.pillButtonText,
                    category === item.key && styles.pillButtonTextActive,
                  ]}
                >
                  {item.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        <View style={styles.row}>
          <View style={[styles.inputGroup, styles.rowItem]}>
            <Text style={styles.inputLabel}>Quantity</Text>
            <TextInput
              value={quantity}
              onChangeText={setQuantity}
              style={styles.textInput}
              keyboardType="numeric"
              placeholder="1"
            />
          </View>
          <View style={[styles.inputGroup, styles.rowItem]}>
            <Text style={styles.inputLabel}>Unit</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {units.map((item) => (
                <TouchableOpacity
                  key={item}
                  style={[
                    styles.pillButton,
                    unit === item && styles.pillButtonActive,
                  ]}
                  onPress={() => setUnit(item)}
                >
                  <Text
                    style={[
                      styles.pillButtonText,
                      unit === item && styles.pillButtonTextActive,
                    ]}
                  >
                    {item}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Expiry Date</Text>
          <View style={styles.expiryRow}>
            <TextInput
              value={expiryMonth}
              onChangeText={setExpiryMonth}
              placeholder="MM"
              keyboardType="numeric"
              maxLength={2}
              style={[styles.textInput, styles.expiryInput]}
            />
            <Text style={styles.expirySeparator}>/</Text>
            <TextInput
              value={expiryDay}
              onChangeText={setExpiryDay}
              placeholder="DD"
              keyboardType="numeric"
              maxLength={2}
              style={[styles.textInput, styles.expiryInput]}
            />
            <Text style={styles.expirySeparator}>/</Text>
            <TextInput
              value={expiryYear}
              onChangeText={setExpiryYear}
              placeholder="YYYY"
              keyboardType="numeric"
              maxLength={4}
              style={[styles.textInput, styles.expiryInput]}
            />
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Notes (optional)</Text>
          <TextInput
            value={notes}
            onChangeText={setNotes}
            placeholder="Add additional notes..."
            style={[styles.textInput, styles.textArea]}
            multiline
          />
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity style={styles.cancelButton} onPress={() => navigation.goBack()}>
          <Text style={styles.cancelButtonText}>Cancel</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.submitButton, disabled && styles.submitButtonDisabled]}
          onPress={handleSubmit}
          disabled={disabled}
        >
          <Text style={styles.submitButtonText}>
            {submitting ? 'Adding...' : 'Add Item'}
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: Platform.OS === 'ios' ? 60 : 30,
    paddingHorizontal: 20,
    paddingBottom: 16,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#E0E0E0',
  },
  backButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#2C3E50',
  },
  headerSpacer: {
    width: 24,
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 20,
    paddingBottom: 40,
    gap: 20,
  },
  inputGroup: {
    gap: 8,
  },
  inputLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2C3E50',
  },
  textInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: '#2C3E50',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  textArea: {
    minHeight: 90,
    textAlignVertical: 'top',
  },
  expiryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  expiryInput: {
    flex: 1,
    textAlign: 'center',
  },
  expirySeparator: {
    fontSize: 18,
    fontWeight: '600',
    color: '#7F8C8D',
  },
  row: {
    flexDirection: 'row',
    gap: 16,
  },
  rowItem: {
    flex: 1,
  },
  pillButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    marginRight: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  pillButtonActive: {
    backgroundColor: '#2196F3',
  },
  pillButtonText: {
    fontSize: 14,
    color: '#7F8C8D',
    fontWeight: '500',
  },
  pillButtonTextActive: {
    color: '#FFFFFF',
  },
  footer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#FFFFFF',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#E0E0E0',
    gap: 16,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#E0E0E0',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#7F8C8D',
  },
  submitButton: {
    flex: 1,
    backgroundColor: '#4CAF50',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});

export default AddPantryItemScreen;

