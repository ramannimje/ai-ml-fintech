import { useEffect, useState, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, TrendingUp, BarChart3, MessageSquare, Settings, Bell, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface CommandItem {
  id: string;
  label: string;
  category: 'navigation' | 'commodity' | 'action';
  path?: string;
  action?: 'refresh';
  shortcut?: string;
  icon?: React.ReactNode;
}

const NAVIGATION_ITEMS: CommandItem[] = [
  { id: 'dashboard', label: 'Dashboard', category: 'navigation', path: '/', shortcut: 'G D' },
  { id: 'chat', label: 'AI Chat', category: 'navigation', path: '/chat', shortcut: 'G A' },
  { id: 'train', label: 'Model Studio', category: 'navigation', path: '/train', shortcut: 'G T' },
  { id: 'profile', label: 'Profile', category: 'navigation', path: '/profile', shortcut: 'G P' },
  { id: 'settings', label: 'Settings', category: 'navigation', path: '/settings', shortcut: 'G S' },
  { id: 'about', label: 'About Us', category: 'navigation', path: '/about' },
];

const COMMODITY_ITEMS: CommandItem[] = [
  { id: 'gold', label: 'Gold', category: 'commodity', path: '/commodity/gold' },
  { id: 'silver', label: 'Silver', category: 'commodity', path: '/commodity/silver' },
  { id: 'crude_oil', label: 'Crude Oil', category: 'commodity', path: '/commodity/crude_oil' },
];

const ACTION_ITEMS: CommandItem[] = [
  { id: 'refresh', label: 'Refresh Data', category: 'action', action: 'refresh', shortcut: 'R' },
];

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Filter items based on query
  const filteredItems = useMemo(() => {
    const allItems = [...NAVIGATION_ITEMS, ...COMMODITY_ITEMS, ...ACTION_ITEMS];
    
    if (!query.trim()) return allItems.slice(0, 8);

    return allItems.filter((item) =>
      item.label.toLowerCase().includes(query.toLowerCase())
    );
  }, [query]);

  // Focus input on open
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredItems.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selectedItem = filteredItems[selectedIndex];
        if (selectedItem?.path) {
          navigate(selectedItem.path);
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, selectedIndex, filteredItems.length, navigate]);

  const handleSelect = (item: CommandItem) => {
    if (item.action === 'refresh') {
      window.location.reload();
    } else if (item.path) {
      navigate(item.path);
    }
    onClose();
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'navigation':
        return <BarChart3 size={16} />;
      case 'commodity':
        return <TrendingUp size={16} />;
      case 'action':
        return <Settings size={16} />;
      default:
        return <Search size={16} />;
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="command-palette-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="command-palette"
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="command-palette-input-wrapper">
            <Search size={20} className="command-palette-icon" />
            <input
              ref={inputRef}
              type="text"
              className="command-palette-input"
              placeholder="Type a command or search..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
            />
            <button className="command-palette-close" onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          <div className="command-palette-results">
            {filteredItems.length === 0 ? (
              <div className="command-palette-empty">
                <Search size={32} className="mb-2 opacity-50" />
                <p className="text-muted">No results found</p>
              </div>
            ) : (
              filteredItems.map((item, index) => (
                <button
                  key={item.id}
                  className={`command-palette-item ${index === selectedIndex ? 'selected' : ''}`}
                  onClick={() => handleSelect(item)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <span className="command-palette-item-icon">
                    {getCategoryIcon(item.category)}
                  </span>
                  <span className="command-palette-item-label">{item.label}</span>
                  {item.shortcut && (
                    <span className="command-palette-shortcut">{item.shortcut}</span>
                  )}
                </button>
              ))
            )}
          </div>

          <div className="command-palette-footer">
            <span className="command-palette-hint">
              <kbd>↑↓</kbd> to navigate
            </span>
            <span className="command-palette-hint">
              <kbd>↵</kbd> to select
            </span>
            <span className="command-palette-hint">
              <kbd>esc</kbd> to close
            </span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// Hook to manage command palette state
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K to open
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
  };
}
