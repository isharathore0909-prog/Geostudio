using System;
using System.Collections.Generic;

namespace GeoStudio.Raster
{
    internal sealed class TileCache
    {
        private readonly long _budget;
        private long _size;
        private readonly object _lock = new();
        private readonly Dictionary<string, LinkedListNode<(string key, byte[] data)>> _map = new();
        private readonly LinkedList<(string key, byte[] data)> _lru = new();

        public TileCache(long budgetBytes)
        {
            _budget = budgetBytes;
        }

        public bool TryGet(string key, out byte[] data)
        {
            lock (_lock)
            {
                if (_map.TryGetValue(key, out var node))
                {
                    _lru.Remove(node);
                    _lru.AddFirst(node);
                    data = node.Value.data;
                    return true;
                }
            }
            data = Array.Empty<byte>();
            return false;
        }

        public void Add(string key, byte[] data)
        {
            lock (_lock)
            {
                if (_map.ContainsKey(key)) return;
                _map[key] = _lru.AddFirst((key, data));
                _size += data.Length;
                while (_size > _budget && _lru.Last != null)
                {
                    var last = _lru.Last;
                    _lru.RemoveLast();
                    _map.Remove(last.Value.key);
                    _size -= last.Value.data.Length;
                }
            }
        }

        public void RemoveLayer(string layerId)
        {
            string prefix = layerId + "|";
            lock (_lock)
            {
                for (var node = _lru.First; node != null;)
                {
                    var next = node.Next;
                    if (node.Value.key.StartsWith(prefix, StringComparison.Ordinal))
                    {
                        _lru.Remove(node);
                        _map.Remove(node.Value.key);
                        _size -= node.Value.data.Length;
                    }
                    node = next;
                }
            }
        }
    }
}
