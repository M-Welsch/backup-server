/**
 * @defgroup    version Software Versioning
 * @brief       Software Versioning Interface
 *
 * @{
 *
 * @file        pcu_version.h
 * @brief       Software Versioning Interface
 *
 * @author      Maxi <maxiwelsch@posteo.de>
 */
#ifndef PCU_VERSION_H_
#define PCU_VERSION_H_

/**
 * @name    Software Versioning symbols
 *
 * Symbols used for software versioning. The symbols are defined in version.c
 * @{
 */
extern const char * pcu_build_git_branch_name;      /**< Current branch name */
extern const char * pcu_build_git_branch_status;    /**< Log if branch has any edits */
extern const char * pcu_build_git_last_commit;      /**< SHA shortened of last commit */
extern const char * pcu_build_git_commit_time;      /**< Date of the last commit */
extern const char * pcu_build_date;                 /**< Firmware Build date */
/** @} */

#endif /* PCU_VERSION_H_ */
/** @} */
