'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Search } from 'lucide-react';

/**
 * Autocomplete Component
 * Provides a searchable dropdown with an "Other" option that reveals a custom text input.
 */
export default function Autocomplete({ 
  options, 
  value, 
  onChange, 
  placeholder, 
  label, 
  icon: Icon,
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
      setQuery('');
      setIsOther(false);
      setCustomValue('');
    } else if (!options.includes(value) && value !== '') {
      // It's a custom value
      setIsOther(true);
      setCustomValue(value);
      setQuery('Other');
    } else {
      setIsOther(false);
      setQuery(value);
    }
  }, [value, options]);

  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (option) => {
    if (option === 'Other') {
      setIsOther(true);
      setQuery('Other');
      onChange(''); // Clear actual value until they type
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
    <div className="relative" ref={wrapperRef}>
      {label && (
        <label className="block text-sm font-semibold text-slate-700 mb-2">
          {label}
        </label>
      )}
      
      <div 
        className={`relative flex items-center border rounded-xl overflow-hidden transition-colors ${
          disabled ? 'bg-slate-50 border-slate-200 opacity-60' : 
          isOpen ? 'border-indigo-500 ring-2 ring-indigo-100' : 'border-slate-300 hover:border-slate-400 bg-white'
        }`}
      >
        {Icon && (
          <div className="pl-3 pr-2 text-slate-400">
            <Icon size={18} />
          </div>
        )}
        
        <input
          type="text"
          className="w-full py-3 px-2 outline-none bg-transparent text-slate-800 placeholder-slate-400 text-sm"
          placeholder={placeholder}
          value={isOther ? 'Other' : query}
          onChange={(e) => {
            if (isOther) {
              setIsOther(false); // If they start typing in the dropdown input, reset Other state
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
          className="px-3 text-slate-400 hover:text-slate-600 transition-colors"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
        >
          <ChevronDown size={18} className={`transform transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Dropdown Menu */}
      {isOpen && !disabled && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-xl shadow-xl max-h-60 overflow-y-auto custom-scrollbar">
          {filteredOptions.length === 0 ? (
            <div className="px-4 py-3 text-sm text-slate-500">No matching options found. Select "Other" to type manually.</div>
          ) : (
            filteredOptions.map((option, idx) => (
              <div
                key={idx}
                className="px-4 py-2.5 text-sm text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 cursor-pointer transition-colors"
                onClick={() => handleSelect(option)}
              >
                {option}
              </div>
            ))
          )}
          
          <div className="border-t border-slate-100 my-1"></div>
          <div
            className="px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 cursor-pointer flex items-center justify-between"
            onClick={() => handleSelect('Other')}
          >
            <span>Other (Type manually)</span>
            <span className="text-xs text-slate-400">Can't find it?</span>
          </div>
        </div>
      )}

      {/* Custom Input Field (Shows only if "Other" is selected) */}
      {isOther && (
        <div className="mt-3 relative">
          <input
            type="text"
            className="w-full py-3 px-4 outline-none border border-amber-300 bg-amber-50 rounded-xl text-slate-800 placeholder-amber-600/50 text-sm focus:ring-2 focus:ring-amber-200 transition-all"
            placeholder={`Please specify your ${label.toLowerCase().replace(' *', '')}...`}
            value={customValue}
            onChange={handleCustomChange}
            autoFocus
          />
        </div>
      )}
    </div>
  );
}
