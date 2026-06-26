'use client';

import { useState, useRef, useEffect } from 'react';

/**
 * Autocomplete Component
 * Uses native globals.css styles (form-input).
 */
export default function Autocomplete({ 
  options, 
  value, 
  onChange, 
  placeholder, 
  label, 
  disabled = false
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [isOther, setIsOther] = useState(false);
  const [customValue, setCustomValue] = useState('');
  const wrapperRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Update internal state if parent changes value
  useEffect(() => {
    if (!value) {
      if (!isOther) {
        setQuery('');
        setCustomValue('');
      }
    } else if (!options.includes(value) && value !== '') {
      setIsOther(true);
      setCustomValue(value);
      setQuery('Other');
    } else {
      setIsOther(false);
      setQuery(value);
    }
  }, [value, options, isOther]);

  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (option) => {
    if (option === 'Other') {
      setIsOther(true);
      setQuery('Other');
      onChange(''); // Parent receives empty string until they type in custom box
    } else {
      setIsOther(false);
      setQuery(option);
      onChange(option);
    }
    setIsOpen(false);
  };

  const handleCustomChange = (e) => {
    setCustomValue(e.target.value);
    onChange(e.target.value);
  };

  return (
    <div style={{ position: 'relative' }} ref={wrapperRef}>
      {label && (
        <label className="form-label">{label}</label>
      )}
      
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <input
          type="text"
          className="form-input"
          style={{ 
             paddingRight: '36px', 
             backgroundColor: disabled ? 'var(--gray-50)' : 'var(--white)',
             cursor: disabled ? 'not-allowed' : 'text',
             opacity: disabled ? 0.7 : 1
          }}
          placeholder={placeholder}
          value={isOther ? 'Other' : query}
          onChange={(e) => {
            if (isOther) {
              setIsOther(false);
              onChange('');
            }
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => !disabled && setIsOpen(true)}
          disabled={disabled}
        />
        
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          style={{
            position: 'absolute',
            right: '12px',
            background: 'none',
            border: 'none',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--gray-400)',
            padding: 4
          }}
        >
          <svg 
            width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" 
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      </div>

      {/* Dropdown Menu */}
      {isOpen && !disabled && (
        <div style={{
          position: 'absolute',
          zIndex: 50,
          width: '100%',
          marginTop: '4px',
          background: 'var(--white)',
          border: '1px solid var(--gray-200)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          maxHeight: '240px',
          overflowY: 'auto'
        }}>
          {filteredOptions.length === 0 ? (
            <div style={{ padding: '12px 16px', fontSize: '13px', color: 'var(--gray-500)' }}>
              No matching options found. Select "Other" to type manually.
            </div>
          ) : (
            filteredOptions.map((option, idx) => (
              <div
                key={idx}
                style={{
                  padding: '10px 16px',
                  fontSize: '14px',
                  color: 'var(--navy-700)',
                  cursor: 'pointer',
                  borderBottom: '1px solid var(--gray-50)',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--primary-50)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                onClick={() => handleSelect(option)}
              >
                {option}
              </div>
            ))
          )}
          
          <div style={{ height: '1px', background: 'var(--gray-100)', margin: '4px 0' }}></div>
          <div
            style={{
              padding: '10px 16px',
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--primary-600)',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: 'var(--gray-50)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--primary-100)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--gray-50)'}
            onClick={() => handleSelect('Other')}
          >
            <span>Other (Type manually)</span>
          </div>
        </div>
      )}

      {/* Custom Input Field (Shows only if "Other" is selected) */}
      {isOther && (
        <div style={{ marginTop: '12px' }}>
          <input
            type="text"
            className="form-input"
            style={{ 
              borderColor: 'var(--amber-500)', 
              backgroundColor: 'var(--amber-50)',
              boxShadow: '0 0 0 3px rgba(245, 158, 11, 0.1)'
            }}
            placeholder={`Please specify...`}
            value={customValue}
            onChange={handleCustomChange}
            autoFocus
          />
        </div>
      )}
    </div>
  );
}
