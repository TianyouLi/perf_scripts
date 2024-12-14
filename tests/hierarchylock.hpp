#pragma once

#include <mutex>
#include <vector>
#include <thread>
#include <atomic>

struct alignas(64) SpinLock {
  std::atomic_bool locker_;
  //char padding[64-sizeof(std::atomic_bool)];
  
  SpinLock():locker_(false) {}
  
  void lock() {
    bool state = false;
    while(!locker_.compare_exchange_weak(state,true,std::memory_order_acquire)) {
      state = false;
    }
  }

  void unlock() {
    locker_.store(false, std::memory_order_release);
  }
};

template <class MutexType>
class HierarchyMutex {
 public:
  HierarchyMutex(unsigned long concurrencyLevel);
  ~HierarchyMutex();
  HierarchyMutex& operator=(const HierarchyMutex&) = delete;
  
 public:
  void lock();
  void unlock();
  bool trylock();

 private:
  MutexType _final;
  std::vector<MutexType> _entries;
  std::hash<std::thread::id> _hasher;
  
  unsigned long _concurrencyLevel;
};

template <class MutexType>
HierarchyMutex<MutexType>::HierarchyMutex(unsigned long concurrencyLevel)
    : _entries(concurrencyLevel)
{
  _concurrencyLevel = concurrencyLevel;
}

template <class MutexType>
HierarchyMutex<MutexType>::~HierarchyMutex()
{
  
}
template <class MutexType>
void HierarchyMutex<MutexType>::lock()
{
  unsigned long index = _hasher(std::this_thread::get_id()) % _concurrencyLevel;

  _entries.at(index).lock();

  _final.lock();
}

template <class MutexType>
void HierarchyMutex<MutexType>::unlock()
{
  unsigned long index = _hasher(std::this_thread::get_id()) % _concurrencyLevel;

  _final.unlock();
  
  _entries.at(index).unlock();
}

template <class MutexType>
bool HierarchyMutex<MutexType>::trylock()
{
  unsigned long index = _hasher(std::this_thread::get_id()) % _concurrencyLevel;

  if ( _entries.at(index).try_lock() ) {
    if ( _final.try_lock()) {
      return true;
    } else {
      _entries.at(index).unlock();
    }
  }

  return false;
}
