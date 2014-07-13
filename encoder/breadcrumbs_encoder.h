
#ifndef __BREADCRUMBS_ENCODER_H__
#define __BREADCRUMBS_ENCODER_H__

#include <stdint.h>

#include "util.h"

#define MAX_FIELD_SIZE 1024
#define MAX_NUM_FIELDS 255
#define MAX_NUM_INPUTS 10000000
#define INVALID_RATIO 0.001

/* We want to filter out all corrupted and invalid timestamps
   but we don't know the exact timerange we should be getting.
   Hence, we assume a reasonable range. */
#define TSTAMP_MIN 1325404800 /* 2012-01-01 */
#define TSTAMP_MAX 1483257600 /* 2017-01-01 */

struct logline{
    uint64_t values_offset;
    uint32_t num_values;
    uint32_t timestamp;
    uint64_t prev_logline_idx;
};


#endif /* __BREADCRUMBS_ENCODER_H__ */
