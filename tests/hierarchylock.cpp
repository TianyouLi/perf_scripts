#include <barrier>
#include <thread>
#include <vector>
#include <iostream>
#include <memory>
#include <climits>

#include "CLI11.hpp"
#include "hierarchylock.hpp"
 
class ThreadCtx {
 public:
  unsigned int index;
  unsigned int lock_type;
  unsigned long iter_count;
  unsigned long work_count;
  std::vector<unsigned int> affinity;
  
  std::shared_ptr<SpinLock> spinlock;
  std::shared_ptr<std::mutex> mutexlock;
  std::shared_ptr<HierarchyMutex<SpinLock>> hierarchylock;
  std::shared_ptr<std::chrono::nanoseconds::rep[]> time_elapsed_per_thread;
  std::shared_ptr<std::barrier<>> start_barrier;
};

void set_affinity(unsigned int id) {
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(id, &cpu_set);

  if (pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpu_set)) {
    std::cout << "Failed to set affinity" << std::endl;
  }
}

void thread_func(std::shared_ptr<ThreadCtx> ctx) {
  char thdname[32];
  snprintf(thdname, sizeof(thdname), "thread_%d", ctx->index);
  pthread_setname_np(pthread_self(), thdname);

  if (ctx->index < ctx->affinity.size()) {
    set_affinity(ctx->affinity[ctx->index]);
  } 
  
  ctx->start_barrier->arrive_and_wait();

  const auto begin = std::chrono::high_resolution_clock::now();

  for (unsigned long i =0; i < ctx->iter_count; i++) {
    switch (ctx->lock_type) {
      case 0:
        ctx->spinlock->lock();
        ctx->spinlock->unlock();
        break;
      case 1:
        ctx->mutexlock->lock();
        ctx->mutexlock->unlock();
        break;
      case 2:
        ctx->hierarchylock->lock();
        ctx->hierarchylock->unlock();
        break;
      default:
        break;
    }
  } 
  
  const auto end = std::chrono::high_resolution_clock::now();

  std::chrono::nanoseconds duration = end - begin;
  
  ctx->time_elapsed_per_thread[ctx->index] = duration.count();
}

typedef std::vector<std::thread> Threads;

int main(const int argc, const char* argv[]) {
  CLI::App app{"Sim MySQL case issue on lock."};

  size_t THREAD_COUNT = 512;
  app.add_option("-t,--thread-count", THREAD_COUNT, "The number of threads during the test.");
  
  unsigned int LOCK_TYPE = 0;
  app.add_option("-l,--lock-type", LOCK_TYPE, "The lock type: 0: spinlock, 1: std::mutex, 2: hierarchylock.");
  
  size_t ITER_COUNT = 100000;
  app.add_option("-i,--test-iterations", ITER_COUNT, "The number of iterations in one loop.");

  std::vector<unsigned int> AFFINITY_LIST;
  app.add_option("-c,--cpu-list", AFFINITY_LIST, "The comma seperated cpu id list")->delimiter(',');
      
  CLI11_PARSE(app, argc, argv);

  auto nthreads = THREAD_COUNT;
  
  // array for holding the time duration
  std::shared_ptr<std::chrono::nanoseconds::rep[]> time_elapsed_per_thread(new std::chrono::nanoseconds::rep[nthreads]);

  // create lock
  std::shared_ptr<SpinLock> spinlock(new SpinLock());
  std::shared_ptr<std::mutex> mutexlock(new std::mutex());
  std::shared_ptr<HierarchyMutex<SpinLock>> hierarchylock(new HierarchyMutex<SpinLock>(std::ceil(std::sqrt(THREAD_COUNT))));
  
  // barrier for trigger start
  std::shared_ptr<std::barrier<>> start_barrier(new std::barrier(nthreads));
  
  Threads threads;
  for (unsigned int i = 0; i < nthreads; i++) {
    std::shared_ptr<ThreadCtx> ctx(new ThreadCtx);
    ctx->index = i;
    ctx->iter_count = ITER_COUNT;
    ctx->lock_type = LOCK_TYPE;
    ctx->affinity = AFFINITY_LIST;
    
    ctx->spinlock = spinlock;
    ctx->mutexlock = mutexlock;
    ctx->hierarchylock = hierarchylock;
    
    ctx->time_elapsed_per_thread = time_elapsed_per_thread;
    ctx->start_barrier = start_barrier;
    threads.push_back(std::thread(::thread_func, ctx));
  }

  for (auto & t : threads) {
    t.join();
  }

  std::chrono::nanoseconds::rep total_counts =0;
  std::chrono::nanoseconds::rep max =0;
  std::chrono::nanoseconds::rep min =LLONG_MAX;
  
  for (unsigned int i =0; i < nthreads; i++) {
    total_counts += time_elapsed_per_thread[i];

    if (max < time_elapsed_per_thread[i]) {
      max = time_elapsed_per_thread[i];
    }

    if (min > time_elapsed_per_thread[i]) {
      min = time_elapsed_per_thread[i];
    }
  }
    
  std::cout << "total   time(ns): \t" << total_counts << std::endl;
  std::cout << "max     time(ns): \t" << max << std::endl;
  std::cout << "min     time(ns): \t" << min << std::endl;
  std::cout << "average time(ns): \t" << total_counts / nthreads << std::endl;


  return 0;
}
