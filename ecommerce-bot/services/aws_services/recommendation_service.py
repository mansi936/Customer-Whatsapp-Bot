import boto3
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Configuration
RECOMMENDER_ARN = os.getenv('RECOMMENDER_ARN', 'arn:aws:personalize:ap-south-1:071126865245:recommender/demo-recommendation-1')
AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')

# Create boto3 client
personalizeRt = boto3.client('personalize-runtime', region_name=AWS_REGION)


def get_recommendations(
    user_id: str,
    recommender_arn: Optional[str] = None,
    num_results: Optional[int] = None,
    filter_arn: Optional[str] = None,
    filter_values: Optional[Dict] = None
) -> List[str]:
    """
    Get recommendations for a specific user from Amazon Personalize.
    
    Args:
        user_id (str): The ID of the user to get recommendations for
        recommender_arn (str, optional): Override default recommender ARN
        num_results (int, optional): Number of recommendations to return
        filter_arn (str, optional): ARN of a filter to apply
        filter_values (dict, optional): Values for filter parameters
    
    Returns:
        List[str]: List of recommended item IDs
    """
    try:
        # Build request parameters
        params = {
            'recommenderArn': recommender_arn or RECOMMENDER_ARN,
            'userId': user_id
        }
        
        if num_results:
            params['numResults'] = num_results
            
        if filter_arn:
            params['filterArn'] = filter_arn
            
        if filter_values:
            params['filterValues'] = filter_values
        
        # Get recommendations
        response = personalizeRt.get_recommendations(**params)
        
        # Extract item IDs
        recommendations = [item['itemId'] for item in response['itemList']]
        
        return recommendations
        
    except Exception as e:
        raise Exception(f"Error getting recommendations: {str(e)}")


def get_recommendations_with_metadata(
    user_id: str,
    recommender_arn: Optional[str] = None,
    num_results: Optional[int] = None,
    metadata_columns: Optional[Dict] = None
) -> List[Dict]:
    """
    Get recommendations with item metadata for a specific user.
    
    Args:
        user_id (str): The ID of the user to get recommendations for
        recommender_arn (str, optional): Override default recommender ARN
        num_results (int, optional): Number of recommendations to return
        metadata_columns (dict, optional): Metadata columns to include
    
    Returns:
        List[Dict]: List of recommendations with item IDs, scores, and metadata
    """
    try:
        # Build request parameters
        params = {
            'recommenderArn': recommender_arn or RECOMMENDER_ARN,
            'userId': user_id
        }
        
        if num_results:
            params['numResults'] = num_results
            
        if metadata_columns:
            params['metadataColumns'] = metadata_columns
        
        # Get recommendations
        response = personalizeRt.get_recommendations(**params)
        
        # Extract items with all data
        recommendations = []
        for item in response['itemList']:
            rec = {
                'itemId': item['itemId'],
                'score': item.get('score', 0.0)
            }
            
            # Add metadata if present
            if 'itemMetadata' in item:
                rec['metadata'] = item['itemMetadata']
                
            recommendations.append(rec)
        
        return recommendations
        
    except Exception as e:
        raise Exception(f"Error getting recommendations with metadata: {str(e)}")


def get_item_recommendations(
    item_id: str,
    recommender_arn: Optional[str] = None,
    num_results: Optional[int] = None
) -> List[str]:
    """
    Get related item recommendations (item-to-item similarity).
    
    Args:
        item_id (str): The ID of the item to get recommendations for
        recommender_arn (str, optional): Override default recommender ARN (must be SIMS recipe)
        num_results (int, optional): Number of recommendations to return
    
    Returns:
        List[str]: List of related item IDs
    """
    try:
        # Build request parameters
        params = {
            'recommenderArn': recommender_arn or RECOMMENDER_ARN,
            'itemId': item_id
        }
        
        if num_results:
            params['numResults'] = num_results
        
        # Get recommendations
        response = personalizeRt.get_recommendations(**params)
        
        # Extract item IDs
        recommendations = [item['itemId'] for item in response['itemList']]
        
        return recommendations
        
    except Exception as e:
        raise Exception(f"Error getting item recommendations: {str(e)}")


if __name__ == "__main__":
    import sys
    
    # Get user ID from command line or prompt
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        user_id = input("Enter user ID: ")
    
    try:
        # Get simple recommendations
        recommendations = get_recommendations(user_id)
        
        print(f"\nRecommended items for user {user_id}:")
        print("-" * 30)
        for item in recommendations:
            print(item)
            
    except Exception as e:
        print(f"Error: {e}")